"""
pipeline.py — Sarvam-native video dubbing pipeline
----------------------------------------------------
STT   : Saaras v3        (chunked, 25s max per REST call)
Trans : Sarvam-Translate v1
TTS   : Bulbul v3
Mux   : FFmpeg

NEW FEATURES:
  ✅ Audio timing auto-fit  — stretch/compress TTS to match original slot
  ✅ Subtitle overlay       — burn translated subtitles onto video
  ✅ Export SRT             — .srt file alongside dubbed video
  ✅ Background music       — retain original BGM using Demucs
"""

import os
import base64
import subprocess
import tempfile
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sarvam-dubber")

SUPPORTED_LANGUAGES = {
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "pa-IN": "Punjabi",
    "od-IN": "Odia",
    "en-IN": "English (Indian)",
}

DEFAULT_SPEAKER = "shubh"
CHUNK_SECONDS   = 25      # Saaras REST API hard limit is 30s
ATEMPO_MIN      = 0.5     # FFmpeg atempo min speed
ATEMPO_MAX      = 2.0     # FFmpeg atempo max speed


# ── Data structures ───────────────────────────────────────────────────────────
@dataclass
class TimedSegment:
    text:  str
    start: float
    end:   float
    speaker: Optional[str] = None


@dataclass
class DubResult:
    output_video:      str
    source_transcript: str
    translated_text:   str
    language:          str
    segment_count:     int
    srt_path:          Optional[str] = None
    subtitled_video:   Optional[str] = None
    audio_path:        Optional[str] = None


# ── Step 1: Extract audio ─────────────────────────────────────────────────────
def extract_audio(video_path: str, out_wav: str) -> None:
    log.info(f"[FFMPEG] Extracting audio → {out_wav}")
    cmd = ["ffmpeg", "-y", "-i", video_path,
           "-ac", "1", "-ar", "16000", "-vn", out_wav]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed:\n{r.stderr}")
    log.info("[FFMPEG] Audio extracted OK")


def get_audio_duration(wav_path: str) -> float:
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", wav_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return float(r.stdout.strip())


def get_video_duration(video_path: str) -> float:
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", video_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return float(r.stdout.strip())


def split_audio(wav_path: str, chunk_dir: str,
                chunk_secs: int = CHUNK_SECONDS) -> list[tuple[str, float]]:
    duration = get_audio_duration(wav_path)
    chunks, start, idx = [], 0.0, 0
    while start < duration:
        chunk_path = os.path.join(chunk_dir, f"chunk_{idx:04d}.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path,
             "-ss", str(start), "-t", str(chunk_secs),
             "-ac", "1", "-ar", "16000", chunk_path],
            capture_output=True,
        )
        chunks.append((chunk_path, start))
        start += chunk_secs
        idx   += 1
    log.info(f"[FFMPEG] Split into {len(chunks)} chunks of {chunk_secs}s")
    return chunks


# ── Step 2: STT — Saaras v3 (chunked) ────────────────────────────────────────
def transcribe_audio(
    client: SarvamAI,
    audio_path: str,
    source_lang: Optional[str] = None,
    chunk_dir: Optional[str] = None,
) -> tuple[str, list[TimedSegment]]:
    duration = get_audio_duration(audio_path)
    log.info(f"[SAARAS] Audio {duration:.1f}s → splitting into {CHUNK_SECONDS}s chunks")

    tmpdir = chunk_dir or tempfile.mkdtemp(prefix="saaras_chunks_")
    chunks = split_audio(audio_path, tmpdir)

    all_segments: list[TimedSegment] = []
    full_parts = []

    for i, (chunk_path, offset) in enumerate(chunks):
        log.info(f"[SAARAS] Chunk {i+1}/{len(chunks)} (offset={offset:.1f}s)")
        with open(chunk_path, "rb") as f:
            kwargs = dict(file=f, model="saaras:v3",
                          mode="transcribe", with_timestamps=True)
            if source_lang:
                kwargs["language_code"] = source_lang
            from sarvamai.core import RequestOptions
            resp = client.speech_to_text.transcribe(
                **kwargs,
                request_options=RequestOptions(timeout_in_seconds=120),
            )

        full_parts.append(resp.transcript)
        log.info(f"  → {resp.transcript[:80]!r}")

        if resp.timestamps and resp.timestamps.words:
            ts = resp.timestamps
            for text, start, end in zip(
                ts.words, ts.start_time_seconds, ts.end_time_seconds
            ):
                all_segments.append(TimedSegment(
                    text=text, start=start + offset, end=end + offset
                ))
        else:
            if resp.transcript.strip():
                all_segments.append(TimedSegment(
                    text=resp.transcript,
                    start=offset,
                    end=offset + CHUNK_SECONDS,
                ))

    full_transcript = " ".join(full_parts)
    log.info(f"[SAARAS] {len(all_segments)} segments, {len(full_transcript)} chars")
    return full_transcript, all_segments


# ── Step 3: Translate — Sarvam-Translate v1 ───────────────────────────────────
def translate_segments(
    client: SarvamAI,
    segments: list[TimedSegment],
    source_lang: str,
    target_lang: str,
) -> list[TimedSegment]:
    log.info(f"[MAYURA] {len(segments)} segments: {source_lang} → {target_lang}")
    if source_lang == target_lang:
        log.warning("[MAYURA] source == target, skipping translation")
        return segments

    translated = []
    for i, seg in enumerate(segments):
        kwargs = {
            "input": seg.text,
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "model": "sarvam-translate:v1",
        }
        resp = client.text.translate(**kwargs)
        log.info(f"  [{i+1}/{len(segments)}] {seg.text[:40]!r} → {resp.translated_text[:40]!r}")
        translated.append(TimedSegment(
            text=resp.translated_text,
            start=seg.start,
            end=seg.end,
            speaker=seg.speaker
        ))
    return translated

# ── NEW: Diarization ──────────────────────────────────────────────────────────
def diarize_audio(audio_path: str, hf_token: str) -> list[tuple[float, float, str]]:
    """Uses pyannote.audio to detect speakers. Returns list of (start, end, speaker_label)."""
    log.info("[DIARIZATION] Running Pyannote Diarization...")
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        log.warning("[DIARIZATION] pyannote.audio not installed.")
        return []
        
    try:
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=hf_token)
        if not pipeline:
            log.warning("[DIARIZATION] Failed to load pyannote pipeline (check token/permissions).")
            return []
        diarization = pipeline(audio_path)
        
        results = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            results.append((turn.start, turn.end, speaker))
        return results
    except Exception as e:
        log.error(f"[DIARIZATION] Error: {e}")
        return []

def assign_speakers_to_segments(
    segments: list[TimedSegment], 
    diarization: list[tuple[float, float, str]],
    default_speaker: str = DEFAULT_SPEAKER
) -> list[TimedSegment]:
    """Assigns the best matching Bulbul speaker to each segment based on diarization overlap."""
    if not diarization:
        return segments
        
    # Find all unique speakers from diarization
    unique_speakers = list(set(s[2] for s in diarization))
    
    # Map pyannote speakers to available Bulbul speakers
    bulbul_voices = ["shubh","priya","rahul","neha","aditya","ritu","rohan","pooja","amit","kavya"]
    speaker_map = {}
    for i, spk in enumerate(unique_speakers):
        speaker_map[spk] = bulbul_voices[i % len(bulbul_voices)]
        
    log.info(f"[DIARIZATION] Mapped speakers: {speaker_map}")

    for seg in segments:
        seg_mid = (seg.start + seg.end) / 2
        
        # Find which diarization turn covers this segment's midpoint
        best_spk = None
        for d_start, d_end, spk in diarization:
            if d_start <= seg_mid <= d_end:
                best_spk = spk
                break
                
        # If midpoint didn't work, find max overlap
        if not best_spk:
            max_overlap = 0
            for d_start, d_end, spk in diarization:
                overlap = max(0, min(seg.end, d_end) - max(seg.start, d_start))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_spk = spk
                    
        if best_spk:
            seg.speaker = speaker_map[best_spk]
        else:
            seg.speaker = default_speaker
            
    return segments


# ── Step 4: TTS — Bulbul v3 ───────────────────────────────────────────────────
def synthesize_segments(
    client: SarvamAI,
    segments: list[TimedSegment],
    target_lang: str,
    speaker: str = DEFAULT_SPEAKER,
    output_dir: str = ".",
) -> list[tuple[TimedSegment, str]]:
    log.info(f"[BULBUL] {len(segments)} segments → {target_lang}")
    results = []
    for i, seg in enumerate(segments):
        current_speaker = seg.speaker if seg.speaker else speaker
        resp = client.text_to_speech.convert(
            text=seg.text,
            language_code=target_lang,
            model="bulbul:v3",
            speaker=current_speaker,
            speech_sample_rate=24000,
            enable_preprocessing=True,
        )
        audio_bytes = base64.b64decode(resp.audios[0])
        seg_path = os.path.join(output_dir, f"seg_{i:04d}.wav")
        with open(seg_path, "wb") as f:
            f.write(audio_bytes)
        log.info(f"  [{i+1}/{len(segments)}] {seg.text[:40]!r} → {seg_path}")
        results.append((seg, seg_path))
    return results


# ── NEW: Audio timing auto-fit ────────────────────────────────────────────────
def fit_audio_to_slot(
    wav_path: str,
    out_path: str,
    slot_duration: float,
    sample_rate: int = 24000,
) -> str:
    """
    Stretch or compress TTS audio to fit within the original segment's time slot.
    Uses FFmpeg atempo (range 0.5–2.0, chained for extremes).
    Returns path to fitted WAV.
    """
    actual = get_audio_duration(wav_path)
    if actual <= 0 or slot_duration <= 0:
        return wav_path

    ratio = actual / slot_duration          # >1 = TTS too long → speed up
    ratio = max(ATEMPO_MIN, min(ATEMPO_MAX * 2, ratio))  # clamp

    if abs(ratio - 1.0) < 0.05:            # within 5% — don't bother
        return wav_path

    # atempo is clamped to [0.5, 2.0]; chain filters for extreme ratios
    if ratio > 2.0:
        # e.g. ratio=3.0 → atempo=2.0,atempo=1.5
        r1 = 2.0
        r2 = ratio / 2.0
        atempo_filter = f"atempo={r1},atempo={r2:.4f}"
    elif ratio < 0.5:
        r1 = 0.5
        r2 = ratio / 0.5
        atempo_filter = f"atempo={r1},atempo={r2:.4f}"
    else:
        atempo_filter = f"atempo={ratio:.4f}"

    log.info(f"[AUTOFIT] {actual:.2f}s → {slot_duration:.2f}s slot (ratio={ratio:.2f}, {atempo_filter})")

    cmd = [
        "ffmpeg", "-y", "-i", wav_path,
        "-filter:a", atempo_filter,
        "-ar", str(sample_rate),
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.warning(f"[AUTOFIT] atempo failed, using original: {r.stderr[:200]}")
        return wav_path
    return out_path


def autofit_segments(
    seg_audio_pairs: list[tuple[TimedSegment, str]],
    output_dir: str,
    sample_rate: int = 24000,
) -> list[tuple[TimedSegment, str]]:
    """Apply timing auto-fit to every segment."""
    log.info(f"[AUTOFIT] Fitting {len(seg_audio_pairs)} segments to original timing")
    fitted = []
    for i, (seg, wav_path) in enumerate(seg_audio_pairs):
        slot = seg.end - seg.start
        out_path = os.path.join(output_dir, f"seg_{i:04d}_fitted.wav")
        fitted_path = fit_audio_to_slot(wav_path, out_path, slot, sample_rate)
        fitted.append((seg, fitted_path))
    return fitted


# ── NEW: Export SRT ───────────────────────────────────────────────────────────
def seconds_to_srt_time(s: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm"""
    ms  = int((s % 1) * 1000)
    s   = int(s)
    h   = s // 3600
    m   = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def export_srt(
    segments: list[TimedSegment],
    output_path: str,
) -> str:
    """Write an SRT subtitle file from timed translated segments."""
    log.info(f"[SRT] Writing {len(segments)} subtitles → {output_path}")
    lines = []
    for i, seg in enumerate(segments, 1):
        start_ts = seconds_to_srt_time(seg.start)
        end_ts   = seconds_to_srt_time(seg.end)
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{seg.text}\n")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info(f"[SRT] Written → {output_path}")
    return output_path


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (255, 255, 255)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def burn_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
    font_size: int = 22,
    font_color: str = "#FFFFFF",
    bg_color: str = "#000000",
) -> str:
    """
    Burn translated subtitles onto the video using Python (OpenCV + PIL).
    (Fallback since Mac's Homebrew FFmpeg might lack the subtitles filter)
    """
    log.info(f"[SUBS] Burning subtitles onto {video_path} using Python...")
    
    try:
        import cv2
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        import pysubs2
        import shutil
        import os
    except ImportError:
        log.warning("[SUBS] Missing dependencies (opencv-python, Pillow, pysubs2). Skipping burn.")
        return video_path
        
    subs = pysubs2.load(srt_path)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        log.warning("[SUBS] Could not open video.")
        return video_path
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",          
        "-i", video_path,   
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-c:a", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-shortest",
        output_path
    ]
    
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
        
    fg_rgb = hex_to_rgb(font_color)
    bg_rgb = hex_to_rgb(bg_color) + (180,)
    
    frame_idx = 0
    sub_idx = 0
    total_subs = len(subs)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        t_ms = (frame_idx / fps) * 1000.0
        
        while sub_idx < total_subs and subs[sub_idx].end < t_ms:
            sub_idx += 1
            
        active_text = None
        if sub_idx < total_subs and subs[sub_idx].start <= t_ms <= subs[sub_idx].end:
            active_text = subs[sub_idx].text.replace('\\N', '\n').replace('\n', ' ')
            
        if active_text:
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
            draw = ImageDraw.Draw(pil_img, "RGBA")
            
            bbox = draw.textbbox((0, 0), active_text, font=font)
            txt_w = bbox[2] - bbox[0]
            txt_h = bbox[3] - bbox[1]
            
            x = (width - txt_w) // 2
            y = height - txt_h - 40
            
            draw.rectangle([x-10, y-10, x+txt_w+10, y+txt_h+10], fill=bg_rgb)
            draw.text((x, y), active_text, font=font, fill=fg_rgb + (255,))
            
            frame = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
            
        try:
            process.stdin.write(frame.tobytes())
        except Exception:
            break
            
        frame_idx += 1
        
    cap.release()
    if process.stdin:
        process.stdin.close()
    process.wait()
    
    if process.returncode != 0:
        log.warning(f"[SUBS] Python subtitle burn failed with FFmpeg exit code {process.returncode}")
        return video_path
        
    log.info(f"[SUBS] Done → {output_path}")
    return output_path


# ── NEW: Watermark ────────────────────────────────────────────────────────────
def add_watermark(video_path: str, watermark_path: str, output_path: str) -> str:
    """Add a watermark image to the top-right corner."""
    log.info(f"[WATERMARK] Adding watermark to {video_path}")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex", "overlay=W-w-10:10",
        "-c:a", "copy",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.warning(f"[WATERMARK] Watermark failed: {r.stderr[:300]}")
        return video_path
    log.info(f"[WATERMARK] Done → {output_path}")
    return output_path


# ── NEW: Extract BGM ──────────────────────────────────────────────────────────
def extract_bgm(audio_path: str, output_dir: str) -> str:
    """Uses Demucs to separate vocals and background music."""
    log.info("[BGM] Running Demucs to separate background music...")
    cmd = [
        "demucs",
        "--two-stems=vocals",
        "-n", "mdx_extra",
        "-o", output_dir,
        audio_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log.warning(f"[BGM] Demucs failed: {r.stderr[:500]}")
        return ""
    
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    bgm_path = os.path.join(output_dir, "mdx_extra", base_name, "no_vocals.wav")
    if os.path.exists(bgm_path):
        log.info(f"[BGM] Extracted BGM to {bgm_path}")
        return bgm_path
    return ""


# ── Step 5: Build audio track + mux ──────────────────────────────────────────
def build_audio_track(
    seg_audio_pairs: list[tuple[TimedSegment, str]],
    video_duration: float,
    output_wav: str,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.5,
    sample_rate: int = 24000,
) -> None:
    log.info(f"[MUX] Building audio track ({video_duration:.1f}s)")

    if len(seg_audio_pairs) == 1 and seg_audio_pairs[0][0].start == 0.0 and not bgm_path:
        import shutil
        shutil.copy(seg_audio_pairs[0][1], output_wav)
        log.info("[MUX] Single segment — copied directly")
        return

    inputs, filter_parts = [], []
    
    if bgm_path:
        inputs += ["-i", bgm_path]
        filter_parts.append(f"[0:a]volume={bgm_volume}[bgm]")
    
    offset = 1 if bgm_path else 0
    
    for i, (seg, wav_path) in enumerate(seg_audio_pairs):
        inputs += ["-i", wav_path]
        delay_ms = int(seg.start * 1000)
        idx = i + offset
        filter_parts.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

    n = len(seg_audio_pairs)
    mix_inputs = ""
    if bgm_path:
        mix_inputs += "[bgm]"
    mix_inputs += "".join(f"[a{i}]" for i in range(n))
    
    total_mix = n + (1 if bgm_path else 0)
    filter_parts.append(f"{mix_inputs}amix=inputs={total_mix}:normalize=0[out]")
    
    filter_complex = ";".join(filter_parts)

    cmd = (
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ar", str(sample_rate),
            "-t", str(video_duration),
            output_wav,
        ]
    )
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg audio track build failed:\n{r.stderr}")
    log.info("[MUX] Audio track built OK")


def mux_video_audio(video_path: str, dubbed_audio: str, output_path: str) -> None:
    log.info(f"[MUX] Muxing → {output_path}")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", dubbed_audio,
        "-c:v", "copy",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest", output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg mux failed:\n{r.stderr}")
    log.info(f"[MUX] Done → {output_path}")


# ── Public entry point ────────────────────────────────────────────────────────
def dub_video(
    video_path:     str,
    target_lang:    str  = "kn-IN",
    source_lang:    Optional[str] = None,
    speaker:        str  = DEFAULT_SPEAKER,
    output_path:    Optional[str] = None,
    autofit:        bool = True,
    burn_subs:      bool = True,
    export_srt:     bool = True,
    keep_bgm:       bool = False,
    bgm_volume:     float = 0.5,
    sub_font_size:  int = 22,
    sub_font_color: str = "#FFFFFF",
    sub_bg_color:   str = "#000000",
    watermark_path: Optional[str] = None,
    do_diarization: bool = False,
    hf_token:       Optional[str] = None,
) -> DubResult:
    """
    Full pipeline: video in → dubbed video (+ optional SRT + subtitled video).

    Args:
        video_path  : Input MP4/MKV/etc.
        target_lang : BCP-47 target language code (default kn-IN).
        source_lang : BCP-47 source language (None = use en-IN).
        speaker     : Bulbul v3 voice name.
        output_path : Output MP4 path (auto if None).
        autofit     : Stretch/compress TTS audio to fit original timing.
        burn_subs   : Burn translated subtitles onto output video.
        export_srt  : Write .srt file alongside output video.
    """
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        raise EnvironmentError("SARVAM_API_KEY not set.")

    client     = SarvamAI(api_subscription_key=api_key)
    video_path = str(Path(video_path).resolve())

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    if output_path is None:
        stem        = Path(video_path).stem
        output_path = str(Path(video_path).parent / f"{stem}_dubbed_{target_lang}.mp4")

    srt_path       = None
    subtitled_path = None

    with tempfile.TemporaryDirectory(prefix="sarvam_dub_") as tmpdir:

        # ── 1. Extract audio
        audio_wav = os.path.join(tmpdir, "source_audio.wav")
        extract_audio(video_path, audio_wav)

        bgm_path = None
        if keep_bgm:
            bgm_path = extract_bgm(audio_wav, tmpdir)

        # ── 2. STT
        transcript, segments = transcribe_audio(
            client, audio_wav, source_lang, chunk_dir=tmpdir
        )
        
        # ── 2b. DIARIZATION
        if do_diarization and hf_token:
            diarization_results = diarize_audio(audio_wav, hf_token)
            segments = assign_speakers_to_segments(segments, diarization_results, speaker)

        # ── 3. Translate
        src = source_lang or "en-IN"
        if src == target_lang:
            src = "en-IN" if target_lang != "en-IN" else "hi-IN"

        translated_segments = translate_segments(client, segments, src, target_lang)
        full_translated     = " ".join(s.text for s in translated_segments)

        # ── 4. TTS
        seg_audio_pairs = synthesize_segments(
            client, translated_segments, target_lang, speaker, tmpdir
        )

        # ── 4b. AUTO-FIT: stretch/compress TTS to match original timing
        if autofit:
            log.info("[AUTOFIT] Fitting TTS audio to original segment timing…")
            seg_audio_pairs = autofit_segments(seg_audio_pairs, tmpdir)

        # ── 4c. EXPORT SRT
        if export_srt and translated_segments:
            srt_out  = output_path.replace(".mp4", ".srt")
            srt_path = export_srt_fn(translated_segments, srt_out)

        # ── 5. Build audio track + mux
        duration   = get_video_duration(video_path)
        dubbed_wav = os.path.join(tmpdir, "dubbed_audio.wav")
        build_audio_track(seg_audio_pairs, duration, dubbed_wav, bgm_path=bgm_path, bgm_volume=bgm_volume)
        mux_video_audio(video_path, dubbed_wav, output_path)

        # ── 5a. Copy Audio-Only
        audio_out = output_path.replace(".mp4", ".wav")
        import shutil
        shutil.copy(dubbed_wav, audio_out)

        # ── 5b. BURN SUBTITLES onto dubbed video
        final_video_path = output_path
        if burn_subs and srt_path and os.path.exists(srt_path):
            subtitled_out  = output_path.replace(".mp4", "_subtitled.mp4")
            subtitled_path = burn_subtitles(video_path=output_path,
                                            srt_path=srt_path,
                                            output_path=subtitled_out,
                                            font_size=sub_font_size,
                                            font_color=sub_font_color,
                                            bg_color=sub_bg_color)
            final_video_path = subtitled_path

        # ── 5c. WATERMARK
        if watermark_path and os.path.exists(watermark_path):
            watermarked_out = final_video_path.replace(".mp4", "_wm.mp4")
            final_video_path = add_watermark(final_video_path, watermark_path, watermarked_out)
            
        if final_video_path != output_path:
            shutil.copy(final_video_path, output_path)
            if subtitled_path:
                subtitled_path = final_video_path

    log.info(f"✅ Done! Output: {output_path}")
    return DubResult(
        output_video      = output_path,
        source_transcript = transcript,
        translated_text   = full_translated,
        language          = target_lang,
        segment_count     = len(segments),
        srt_path          = srt_path,
        subtitled_video   = subtitled_path,
        audio_path        = audio_out,
    )


# alias so the inner function name doesn't clash
export_srt_fn = export_srt
