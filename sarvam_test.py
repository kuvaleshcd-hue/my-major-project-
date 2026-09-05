#!/usr/bin/env python3
"""
sarvam_test.py — API sanity check (run this FIRST after getting your API key)
Tests STT (Saaras v3) and TTS (Bulbul v3) with minimal real audio.
Usage:
    python sarvam_test.py
    python sarvam_test.py --audio demo_clip.wav  # test STT on your own file
"""

import os
import sys
import base64
import argparse
import subprocess
import tempfile
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()


def make_test_wav(path: str, duration: float = 2.0) -> None:
    """Generate a short silent WAV for API connectivity test (no real audio needed)."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-ar", "16000", "-ac", "1",
        path,
    ]
    subprocess.run(cmd, capture_output=True)


def test_stt(client: SarvamAI, audio_path: str) -> bool:
    print(f"\n── STT Test (Saaras v3) ───────────────────────────────")
    print(f"   File: {audio_path}")
    try:
        with open(audio_path, "rb") as f:
            resp = client.speech_to_text.transcribe(
                file=f,
                model="saaras:v3",
                mode="transcribe",
                with_timestamps=True,
            )
        print(f"   ✅ transcript : {resp.transcript!r}")
        print(f"   ✅ lang_code  : {resp.language_code}")
        if resp.timestamps:
            print(f"   ✅ segments   : {len(resp.timestamps.words)}")
        return True
    except Exception as e:
        print(f"   ❌ STT FAILED: {e}")
        return False


def test_translate(client: SarvamAI) -> bool:
    print(f"\n── Translation Test (Sarvam-Translate v1) ─────────────")
    test_text = "Hello, this is a test of the translation system."
    print(f"   Input: {test_text!r}")
    try:
        resp = client.text.translate(
            input=test_text,
            source_language_code="en-IN",
            target_language_code="kn-IN",
            model="sarvam-translate:v1",
        )
        print(f"   ✅ Kannada: {resp.translated_text!r}")
        resp2 = client.text.translate(
            input=test_text,
            source_language_code="en-IN",
            target_language_code="hi-IN",
            model="sarvam-translate:v1",
        )
        print(f"   ✅ Hindi  : {resp2.translated_text!r}")
        return True
    except Exception as e:
        print(f"   ❌ Translation FAILED: {e}")
        return False


def test_tts(client: SarvamAI, out_dir: str) -> bool:
    print(f"\n── TTS Test (Bulbul v3) ────────────────────────────────")
    test_phrases = [
        ("kn-IN", "ನಮಸ್ಕಾರ, ಇದು ಸರ್ವಮ್ ಧ್ವನಿ ಪರೀಕ್ಷೆ"),
        ("hi-IN", "नमस्ते, यह सर्वम् आवाज़ परीक्षण है"),
    ]
    all_ok = True
    for lang, text in test_phrases:
        print(f"   [{lang}] {text!r}")
        try:
            resp = client.text_to_speech.convert(
                text=text,
                language_code=lang,
                model="bulbul:v3",
                speaker="shubh",
                speech_sample_rate=24000,
            )
            audio_bytes = base64.b64decode(resp.audios[0])
            out_path = os.path.join(out_dir, f"tts_test_{lang}.wav")
            with open(out_path, "wb") as f:
                f.write(audio_bytes)
            size_kb = len(audio_bytes) / 1024
            print(f"   ✅ {out_path}  ({size_kb:.1f} KB)")
        except Exception as e:
            print(f"   ❌ TTS FAILED for {lang}: {e}")
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Sarvam API sanity check")
    parser.add_argument("--audio", default=None, help="Optional: WAV file for STT test")
    args = parser.parse_args()

    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("❌  SARVAM_API_KEY not set.")
        print("    Copy .env.example → .env, then paste your key.")
        sys.exit(1)

    print(f"🔑  API key found ({api_key[:8]}…)")
    client = SarvamAI(api_subscription_key=api_key)

    results = {}

    with tempfile.TemporaryDirectory(prefix="sarvam_test_") as tmpdir:
        # STT test
        if args.audio:
            stt_file = args.audio
        else:
            stt_file = os.path.join(tmpdir, "test_tone.wav")
            make_test_wav(stt_file)
            print(f"   (no --audio provided, using generated tone for connectivity test)")

        results["STT"]         = test_stt(client, stt_file)
        results["Translation"] = test_translate(client)
        results["TTS"]         = test_tts(client, tmpdir)

        print(f"\n── Results ─────────────────────────────────────────────")
        all_pass = True
        for name, ok in results.items():
            status = "✅ PASS" if ok else "❌ FAIL"
            print(f"   {status}  {name}")
            if not ok:
                all_pass = False

        if all_pass:
            print(f"\n🎉  All checks passed — you're ready to run the pipeline!")
            print(f"    python dub.py demo_clip.mp4 --lang kn-IN")
        else:
            print(f"\n⚠️   Some checks failed — fix before running the full pipeline.")
            sys.exit(1)


if __name__ == "__main__":
    main()
