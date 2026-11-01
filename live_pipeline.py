"""
live_pipeline.py — Sarvam-native Real-Time Live Dubbing & Live Subtitles Engine
-------------------------------------------------------------------------------
Pipeline:
  1. Live Audio Capture   : 16 kHz mono 16-bit PCM (Microphone / stream)
  2. Realtime STT         : Saaras v3 Realtime (WebSocket streaming)
                            -> Live partial subtitles + final utterances
  3. Realtime Translation : Sarvam-Translate v1 (on final utterances)
                            -> Live translated dual subtitles
  4. Realtime TTS         : Bulbul v3 Streaming (WebSocket convert + flush)
                            -> Real-time audio playback (speakers)

Supports:
  - Dual live subtitle events (original partials/finals & translated captions)
  - Thread-safe callbacks for Streamlit UI or web integration
  - Low-latency macOS CoreAudio (afplay) / sounddevice playback
  - SRT and text transcript export
"""

import asyncio
import base64
import io
import logging
import os
import queue
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Sarvam imports
from sarvamai import AsyncSarvamAI, SarvamAI
from sarvamai.types.realtime_audio_input import RealtimeAudioInput
from sarvamai.types.realtime_end import RealtimeEnd

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except (ImportError, OSError):
    HAS_SOUNDDEVICE = False

try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

log = logging.getLogger("live-dubber")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SUPPORTED_LANGUAGES: Dict[str, str] = {
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


@dataclass
class SubtitleItem:
    index: int
    timestamp: str
    source_text: str
    translated_text: str
    start_time: float
    end_time: Optional[float] = None
    is_final: bool = True


class LiveDubSession:
    """
    Manages a continuous bidirectional live dubbing session.
    Streams microphone audio to Sarvam Realtime STT,
    translates completed utterances, and plays streaming TTS.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        source_lang: str = "en-IN",
        target_lang: str = "kn-IN",
        speaker: str = DEFAULT_SPEAKER,
        play_audio: bool = True,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 100,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str, str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is required for live dubbing.")

        self.source_lang = source_lang
        self.target_lang = target_lang
        self.speaker = speaker
        self.play_audio = play_audio
        self.sample_rate = sample_rate
        self.chunk_size = int(sample_rate * (chunk_duration_ms / 1000.0))

        # Callbacks
        self.on_partial = on_partial
        self.on_final = on_final
        self.on_status = on_status

        # State tracking
        self.is_running = False
        self.current_partial: str = ""
        self.current_translated: str = ""
        self.subtitles: List[SubtitleItem] = []
        self.status: str = "Idle"
        self.start_timestamp: float = 0.0

        # Audio streaming queues and threads
        self.audio_queue: Optional[asyncio.Queue] = None
        self.playback_queue: queue.Queue = queue.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._playback_thread: Optional[threading.Thread] = None
        self._sd_stream = None

    def _update_status(self, new_status: str):
        self.status = new_status
        if self.on_status:
            try:
                self.on_status(new_status)
            except Exception as e:
                log.warning(f"Error in on_status callback: {e}")

    def start(self):
        """Start the live dubbing session in a background thread."""
        if self.is_running:
            return
        self.is_running = True
        self.start_timestamp = time.time()
        self._update_status("Starting...")

        self._playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self._playback_thread.start()

        self._worker_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._worker_thread.start()
        log.info(f"Live dubbing session started: {self.source_lang} -> {self.target_lang} ({self.speaker})")

        self._stop_event: Optional[asyncio.Event] = None

    def stop(self):
        """Stop the live dubbing session cleanly."""
        if not self.is_running:
            return
        log.info("Stopping live dubbing session...")
        self.is_running = False
        self._update_status("Stopping...")

        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception as e:
                log.warning(f"Error stopping audio input stream: {e}")
            self._sd_stream = None

        if self._loop and self._loop.is_running() and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)

        self.playback_queue.put(None)  # Sentinel to stop playback worker
        self._update_status("Stopped")
        log.info("Live dubbing session stopped.")

    def _run_async_loop(self):
        """Entry point for background thread running asyncio."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._live_dub_async())
        except Exception as e:
            log.error(f"Error in live dubbing async worker: {e}", exc_info=True)
        finally:
            try:
                # Cancel remaining tasks if any
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()

    async def _live_dub_async(self):
        """Main async pipeline loop connecting STT, Translation, and TTS."""
        client = AsyncSarvamAI(api_subscription_key=self.api_key)
        self.audio_queue = asyncio.Queue()

        # Start microphone recording if sounddevice is available
        if HAS_SOUNDDEVICE:
            def audio_callback(indata, frames, time_info, status):
                if status:
                    log.warning(f"Audio input status: {status}")
                if self.is_running:
                    raw_pcm = indata.tobytes()
                    if self._loop and self.audio_queue:
                        self._loop.call_soon_threadsafe(self.audio_queue.put_nowait, raw_pcm)

            try:
                self._sd_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="int16",
                    blocksize=self.chunk_size,
                    callback=audio_callback,
                )
                self._sd_stream.start()
                self._update_status("Listening 🟢")
            except Exception as e:
                log.error(f"Failed to open microphone input stream: {e}")
                self._update_status(f"Mic Error: {e}")
                return

        self._stop_event = asyncio.Event()

        # 1. Connect to Realtime STT
        stt_context = client.speech_to_text_realtime_streaming.connect(
            language_code=self.source_lang,
            model="saaras:v3-realtime",
            stream_type="fast",
            encoding="linear16",
            sample_rate=str(self.sample_rate),
        )

        # 2. Connect to Streaming TTS
        tts_context = client.text_to_speech_streaming.connect(
            model="bulbul:v3",
            send_completion_event="true",
        )

        try:
            async with stt_context as stt_ws, tts_context as tts_ws:
                # Wait for session.begin
                await stt_ws.recv()

                # Configure TTS output voice and parameters
                await tts_ws.configure(
                    target_language_code=self.target_lang,
                    speaker=self.speaker,
                    min_buffer_size=30,
                    output_audio_codec="mp3",
                )
                log.info("STT and TTS streaming channels initialized successfully.")

                async def send_audio_loop():
                    """Continuously pulls PCM audio from queue and streams to Sarvam STT."""
                    try:
                        while self.is_running:
                            try:
                                chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=0.2)
                                b64_audio = base64.b64encode(chunk).decode("utf-8")
                                await stt_ws.send_realtime_audio_input(RealtimeAudioInput(audio=b64_audio))
                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                if self.is_running:
                                    log.warning(f"Error sending audio chunk: {e}")
                                break

                        # Send session end on termination
                        try:
                            await stt_ws.send_realtime_end(RealtimeEnd())
                        except Exception:
                            pass
                    except asyncio.CancelledError:
                        pass

                async def receive_stt_loop():
                    """Listens for STT partials and final utterances, triggers translation & TTS."""
                    try:
                        while self.is_running:
                            msg = await stt_ws.recv()
                            event = getattr(msg, "event", None)

                            if event == "transcript.partial":
                                partial_text = getattr(msg, "text", "").strip()
                                if partial_text:
                                    self.current_partial = partial_text
                                    self._update_status("Transcribing 🟡")
                                    if self.on_partial:
                                        self.on_partial(partial_text)

                            elif event == "transcript.final":
                                final_text = getattr(msg, "text", "").strip()
                                if not final_text:
                                    continue

                                self.current_partial = final_text
                                self._update_status("Translating 🟣")

                                # Translate utterance
                                try:
                                    trans_resp = await client.text.translate(
                                        input=final_text,
                                        source_language_code=self.source_lang,
                                        target_language_code=self.target_lang,
                                        model="sarvam-translate:v1",
                                    )
                                    translated_text = trans_resp.translated_text.strip()
                                except Exception as te:
                                    log.warning(f"Translation error: {te}")
                                    translated_text = final_text

                                self.current_translated = translated_text
                                elapsed = time.time() - self.start_timestamp
                                time_str = datetime.utcfromtimestamp(elapsed).strftime("%M:%S")

                                item = SubtitleItem(
                                    index=len(self.subtitles) + 1,
                                    timestamp=time_str,
                                    source_text=final_text,
                                    translated_text=translated_text,
                                    start_time=elapsed,
                                )
                                self.subtitles.append(item)

                                if self.on_final:
                                    self.on_final(final_text, translated_text)

                                # If play_audio enabled, convert with Bulbul TTS
                                if self.play_audio and translated_text:
                                    self._update_status("Dubbing 🔊")
                                    try:
                                        await tts_ws.convert(text=translated_text)
                                        await tts_ws.flush()
                                    except Exception as ttse:
                                        log.warning(f"TTS convert error: {ttse}")

                                self._update_status("Listening 🟢")

                            elif event == "session.end":
                                break

                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        if self.is_running:
                            log.error(f"Error receiving STT messages: {e}")

                async def receive_tts_loop():
                    """Collects streamed MP3 audio chunks from Bulbul and pushes to playback queue."""
                    accumulated_mp3 = bytearray()
                    try:
                        while self.is_running:
                            msg = await tts_ws.recv()
                            msg_type = getattr(msg, "type", None)

                            if msg_type == "audio":
                                if hasattr(msg, "data") and hasattr(msg.data, "audio"):
                                    raw_bytes = base64.b64decode(msg.data.audio)
                                    accumulated_mp3.extend(raw_bytes)

                            elif msg_type == "event":
                                event_type = getattr(msg.data, "event_type", None)
                                if event_type == "final":
                                    if accumulated_mp3:
                                        self.playback_queue.put(bytes(accumulated_mp3))
                                        accumulated_mp3.clear()

                            elif msg_type == "error":
                                log.warning(f"TTS Streaming returned error: {msg}")

                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        if self.is_running:
                            log.error(f"Error in TTS receiver loop: {e}")

                send_task = asyncio.create_task(send_audio_loop())
                stt_task = asyncio.create_task(receive_stt_loop())
                tts_task = asyncio.create_task(receive_tts_loop())
                stop_task = asyncio.create_task(self._stop_event.wait())

                done, pending = await asyncio.wait(
                    [send_task, stt_task, tts_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

        except Exception as e:
            log.error(f"Live dubbing session connection failed: {e}")
            self._update_status(f"Error: {e}")

    def _playback_worker(self):
        """Worker thread that takes completed MP3 utterance buffers and plays them."""
        while self.is_running:
            try:
                audio_data = self.playback_queue.get(timeout=0.3)
                if audio_data is None:
                    break

                self._play_audio_bytes(audio_data)
                self.playback_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                log.warning(f"Error in audio playback worker: {e}")

    def _play_audio_bytes(self, mp3_bytes: bytes):
        """Plays MP3 audio bytes using afplay on macOS or pydub fallback."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(mp3_bytes)
                temp_path = f.name

            # On macOS, afplay provides ultra-low latency native playback
            cmd = ["afplay", temp_path]
            subprocess.run(cmd, capture_output=True)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        except Exception as e:
            log.warning(f"afplay playback failed: {e}")

    def export_srt(self) -> str:
        """Export accumulated live subtitles as a standard SubRip (.srt) string."""
        lines = []
        for i, sub in enumerate(self.subtitles, start=1):
            start_s = sub.start_time
            end_s = sub.end_time if sub.end_time else start_s + 3.0

            def fmt_time(seconds: float) -> str:
                hrs = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds - int(seconds)) * 1000)
                return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

            lines.append(str(i))
            lines.append(f"{fmt_time(start_s)} --> {fmt_time(end_s)}")
            lines.append(f"{sub.translated_text}")
            lines.append(f"({sub.source_text})")
            lines.append("")

        return "\n".join(lines)

    def export_text(self) -> str:
        """Export session transcript as formatted text."""
        lines = [f"# Live Dubbing Session Transcript ({self.source_lang} -> {self.target_lang})\n"]
        for sub in self.subtitles:
            lines.append(f"[{sub.timestamp}]")
            lines.append(f"  Original   : {sub.source_text}")
            lines.append(f"  Dubbed     : {sub.translated_text}")
            lines.append("")
        return "\n".join(lines)


# ── Interactive CLI runner ───────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zivana Live Dubbing & Subtitles (Realtime Mic)")
    parser.add_argument("--lang", "-l", default="kn-IN", help="Target language (default: kn-IN)")
    parser.add_argument("--source", "-s", default="en-IN", help="Source language (default: en-IN)")
    parser.add_argument("--speaker", default=DEFAULT_SPEAKER, help="Bulbul speaker voice")
    parser.add_argument("--mute", action="store_true", help="Only show live subtitles, mute voice dubbing")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("🎙️  ZIVANA — Real-Time Live Dubbing & Live Subtitles")
    print("=" * 65)
    print(f"  • Source Language : {SUPPORTED_LANGUAGES.get(args.source, args.source)}")
    print(f"  • Target Language : {SUPPORTED_LANGUAGES.get(args.lang, args.lang)}")
    print(f"  • Voice Speaker   : {args.speaker}")
    print(f"  • Audio Dubbing   : {'Muted (Subtitles Only)' if args.mute else 'Enabled (MacBook Speakers)'}")
    print("=" * 65)
    print("\nSpeak into your microphone. Press Ctrl+C to stop.\n")

    def on_partial(text):
        print(f"\r💬 [LIVE]: {text}...", end="", flush=True)

    def on_final(source, trans):
        print(f"\r" + " " * 80 + "\r", end="")
        print(f"🎙️ Original  : {source}")
        print(f"🔊 Dubbed ({args.lang}) : \033[1;32m{trans}\033[0m\n")

    session = LiveDubSession(
        source_lang=args.source,
        target_lang=args.lang,
        speaker=args.speaker,
        play_audio=not args.mute,
        on_partial=on_partial,
        on_final=on_final,
    )

    try:
        session.start()
        while session.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nStopping live session...")
        session.stop()
        print("\n📄 Session Transcript Summary:")
        print(session.export_text())
        print("Done!")


if __name__ == "__main__":
    main()
