#!/usr/bin/env python3
"""
dub.py — CLI for Sarvam-native VideoDubber
Usage:
    python dub.py demo_clip.mp4 --lang kn-IN
    python dub.py demo_clip.mp4 --lang hi-IN --speaker ananya
    python dub.py demo_clip.mp4 --lang kn-IN --source en-IN --out output/dubbed.mp4
"""

import argparse
import sys
from pipeline import dub_video, SUPPORTED_LANGUAGES, DEFAULT_SPEAKER


def main():
    parser = argparse.ArgumentParser(
        description="Sarvam-native video dubber (Saaras + Sarvam-Translate + Bulbul)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dub.py demo_clip.mp4
  python dub.py demo_clip.mp4 --lang hi-IN
  python dub.py demo_clip.mp4 --lang kn-IN --speaker ananya
  python dub.py demo_clip.mp4 --lang ta-IN --source en-IN --out output/tamil_dub.mp4

Supported target languages:
""" + "\n".join(f"  {code}  {name}" for code, name in SUPPORTED_LANGUAGES.items()),
    )

    parser.add_argument("video", help="Path to input video file (MP4, MKV, etc.)")
    parser.add_argument(
        "--lang", "-l",
        default="kn-IN",
        metavar="LANG_CODE",
        help="Target language BCP-47 code (default: kn-IN / Kannada)",
    )
    parser.add_argument(
        "--source", "-s",
        default=None,
        metavar="LANG_CODE",
        help="Source language BCP-47 code (default: auto-detect)",
    )
    parser.add_argument(
        "--speaker",
        default=DEFAULT_SPEAKER,
        metavar="NAME",
        help=f"Bulbul v3 speaker voice (default: {DEFAULT_SPEAKER})",
    )
    parser.add_argument(
        "--out", "-o",
        default=None,
        metavar="OUTPUT_PATH",
        help="Output file path (default: <input>_dubbed_<lang>.mp4)",
    )

    args = parser.parse_args()

    if args.lang not in SUPPORTED_LANGUAGES:
        print(f"❌ Unknown language code: {args.lang}")
        print(f"   Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}")
        sys.exit(1)

    print(f"\n🎬  Zivana")
    print(f"    Input  : {args.video}")
    print(f"    Target : {SUPPORTED_LANGUAGES[args.lang]} ({args.lang})")
    print(f"    Source : {args.source or 'auto-detect'}")
    print(f"    Speaker: {args.speaker}")
    print(f"    Output : {args.out or 'auto'}\n")

    try:
        result = dub_video(
            video_path=args.video,
            target_lang=args.lang,
            source_lang=args.source,
            speaker=args.speaker,
            output_path=args.out,
        )
        print(f"\n✅  Done!")
        print(f"    Output video    : {result.output_video}")
        print(f"    Segments dubbed : {result.segment_count}")
        print(f"    Transcript      : {result.source_transcript[:120]}…")
        print(f"    Translation     : {result.translated_text[:120]}…")

    except EnvironmentError as e:
        print(f"\n❌  Config error: {e}")
        print("    Add SARVAM_API_KEY=your_key to a .env file in this directory.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌  Pipeline error: {e}")
        raise


if __name__ == "__main__":
    main()
