"""
app.py — Zivana · Multi-Language Video Dubber
Tabs: 📁 Upload Video | 🎬 YouTube URL
Features: Auto-fit timing | Subtitle overlay | SRT export
Run: streamlit run app.py
"""

import os
import re
import tempfile
import time
import subprocess
import shutil
from pathlib import Path

import streamlit as st
import db
import login

db.init_db()
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Zivana",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Login gate ─────────────────────────────────────────────────────────────────
if not login.show_login_page():
    st.stop()

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .hero {
    background: linear-gradient(135deg, #22d3ee, #0891b2);
    border-radius: 16px; padding: 2.2rem 2rem;
    margin-bottom: 1.5rem; text-align: center; color: white;
  }
  .hero h1 { font-size: 2.2rem; font-weight: 700; margin: 0; }
  .hero p  { font-size: 0.95rem; opacity: 0.9; margin: 0.4rem 0 0; }
  .pipeline-row { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-top:1rem; }
  .badge {
    background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4);
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.76rem; color: #ffffff; font-weight: 500;
  }
  .feature-badge {
    background: #ecfeff; border: 1px solid #67e8f9;
    border-radius: 20px; padding: 4px 14px;
    font-size: 0.76rem; color: #0e7490; font-weight: 600;
    display: inline-block; margin: 3px;
  }
  .tx-box {
    background: white; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 0.8rem 1rem;
    font-size: 0.85rem; line-height: 1.6;
    max-height: 130px; overflow-y: auto; color: #374151;
  }
  @keyframes pulse-live {
    0% { transform: scale(0.95); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.8; }
  }
  .live-pulse {
    display: inline-block;
    width: 10px; height: 10px;
    background-color: #22c55e;
    border-radius: 50%;
    margin-right: 8px;
    animation: pulse-live 1.5s infinite ease-in-out;
  }
  .live-status-pill {
    display: inline-flex;
    align-items: center;
    background: #0f172a;
    color: #e2e8f0;
    padding: 6px 16px;
    border-radius: 9999px;
    font-size: 0.85rem;
    font-weight: 600;
    border: 1px solid #334155;
    margin-bottom: 1rem;
  }
  .teleprompter-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  }
  .teleprompter-target {
    background: linear-gradient(135deg, #0e7490 0%, #155e75 100%);
    color: #ffffff;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    box-shadow: 0 10px 15px -3px rgba(14, 116, 144, 0.2);
  }
  .teleprompter-title {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .teleprompter-text {
    font-size: 1.35rem;
    font-weight: 600;
    line-height: 1.5;
    min-height: 48px;
  }
  .sub-history-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    max-height: 280px;
    overflow-y: auto;
  }
  #MainMenu {visibility:hidden;} footer {visibility:hidden;} header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🎙️ Zivana</h1>
  <p>Dub any video into Indian languages — upload a file, paste YouTube, or dub Live from Microphone.</p>
  <div class="pipeline-row">
    <span class="badge">🎤 Saaras v3 · STT</span>
    <span class="badge">🌐 Sarvam-Translate v1</span>
    <span class="badge">🔊 Bulbul v3 · TTS</span>
    <span class="badge">🎬 FFmpeg · Mux</span>
  </div>
  <div style="margin-top:10px">
    <span class="feature-badge">🎙️ Live Dubbing & Subtitles</span>
    <span class="feature-badge">⏱️ Auto-fit timing</span>
    <span class="feature-badge">📝 Subtitle overlay</span>
    <span class="feature-badge">💾 SRT export</span>
    <span class="feature-badge">▶️ YouTube support</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
from pipeline import SUPPORTED_LANGUAGES, DEFAULT_SPEAKER

with st.sidebar:
    # ── User info & logout ─────────────────────────────────────────
    sidebar_col1, sidebar_col2 = st.columns([2, 1])
    with sidebar_col1:
        username = st.session_state.get('username', 'User')
        auth_method = st.session_state.get('auth_method', 'password')
        badge = "🔵 Google" if auth_method == "google" else "🔑 Local"
        st.markdown(f"👋 **{username}**  \n<small>{badge}</small>", unsafe_allow_html=True)
    with sidebar_col2:
        if st.button("Logout", key="logout_btn", type="secondary"):
            login.do_logout()
    st.divider()


    st.markdown("### 🔊 Voice")
    SPEAKERS = [
        "shubh","aditya","ritu","priya","neha","rahul",
        "pooja","rohan","simran","kavya","amit","dev",
        "ishita","shreya","anushka","manisha","karun","hitesh",
    ]
    speaker = st.selectbox("Bulbul v3 speaker", SPEAKERS, index=0)

    st.divider()
    st.markdown("### 📹 Source language")
    src_options = {"Auto-detect (en-IN)": "en-IN"} | {
        f"{v} ({k})": k for k, v in SUPPORTED_LANGUAGES.items()
    }
    src_choice  = st.selectbox("Source language", list(src_options.keys()), index=0)
    source_lang = src_options[src_choice]

    st.divider()
    st.markdown("### ✨ Features")
    do_autofit   = st.toggle("⏱️ Auto-fit timing",    value=True,
                              help="Stretch/compress TTS audio to match original segment duration")
                              
    do_subtitles = st.toggle("📝 Burn subtitles",     value=True,
                              help="Burn translated text onto the video")
    if do_subtitles:
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1: sub_font_size = st.number_input("Size", 10, 72, 22)
        with sub_col2: sub_font_color = st.color_picker("Text", "#FFFFFF")
        with sub_col3: sub_bg_color = st.color_picker("Bg", "#000000")
        
        sub_col4, sub_col5 = st.columns(2)
        with sub_col4: sub_font_name = st.selectbox("Font", ["Arial", "Helvetica", "Courier"])
        with sub_col5: sub_position = st.selectbox("Position", ["bottom", "middle", "top"])
    else:
        sub_font_size = 22; sub_font_color = "#FFFFFF"; sub_bg_color = "#000000"
        sub_font_name = "Arial"; sub_position = "bottom"

    do_srt       = st.toggle("💾 Export SRT file",    value=True,
                              help="Download .srt subtitle file")
    do_bgm       = st.toggle("🎵 Keep background music", value=False,
                              help="Retain original background music using Demucs AI (takes longer)")
    if do_bgm:
        bgm_volume = st.slider("BGM Volume", 0.0, 2.0, 0.5, 0.1)
    else:
        bgm_volume = 0.5

    st.divider()
    st.markdown("""
    <div style='font-size:0.78rem;color:#888;line-height:1.8'>
    ⚡ <b>Sarvam BuildIn' Hours</b><br>
    🔗 <a href='https://dashboard.sarvam.ai' target='_blank'>dashboard.sarvam.ai</a>
    </div>
    """, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
LANG_EMOJI = {
    "kn-IN":"🟠","hi-IN":"🟢","ta-IN":"🔵","te-IN":"🟣",
    "ml-IN":"🟡","mr-IN":"🔴","bn-IN":"🟤","gu-IN":"⚪",
    "pa-IN":"🔶","od-IN":"🔷","en-IN":"🏴",
}

def trim_video(input_path: str, start: int, end: int) -> str:
    out = input_path.replace(".mp4", "_trimmed.mp4")
    cmd = ["ffmpeg", "-y", "-i", input_path]
    if start > 0:
        cmd += ["-ss", str(start)]
    if end > 0:
        cmd += ["-to", str(end)]
    cmd += ["-c", "copy", out]
    subprocess.run(cmd, capture_output=True)
    return out


def language_selector(key_prefix: str) -> list[str]:
    if f"{key_prefix}_langs" not in st.session_state:
        st.session_state[f"{key_prefix}_langs"] = ["kn-IN"]
    st.markdown("#### 🌍 Target languages")
    st.caption("Pick one or more — each gets its own dubbed video")
    cols = st.columns(3)
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES.items()):
        with cols[i % 3]:
            checked = st.checkbox(
                f"{LANG_EMOJI.get(code,'🌐')} {name}",
                value=(code in st.session_state[f"{key_prefix}_langs"]),
                key=f"{key_prefix}_lang_{code}",
            )
            if checked and code not in st.session_state[f"{key_prefix}_langs"]:
                st.session_state[f"{key_prefix}_langs"].append(code)
            elif not checked and code in st.session_state[f"{key_prefix}_langs"]:
                st.session_state[f"{key_prefix}_langs"].remove(code)
    selected = st.session_state[f"{key_prefix}_langs"]
    if selected:
        st.caption(f"**{len(selected)} selected:** {', '.join(SUPPORTED_LANGUAGES[l] for l in selected)}")
    return selected


def show_result(r: dict, stem: str):
    """Render one dub result — videos, downloads, transcripts."""
    result = r["result"]

    # ── Tabs: dubbed | subtitled | transcripts | audio
    tab_labels = ["🎬 Dubbed video"]
    if r.get("subtitled_bytes"):
        tab_labels.append("📝 With subtitles")
    if r.get("audio_bytes"):
        tab_labels.append("🎵 Audio Only")
    tab_labels.append("📄 Transcripts")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    with tabs[tab_idx]:
        st.video(r["video_bytes"])
        st.download_button(
            f"⬇️ Download dubbed MP4",
            data=r["video_bytes"],
            file_name=f"{stem}_dubbed_{r['lang_code']}.mp4",
            mime="video/mp4",
            use_container_width=True,
            key=f"dl_dub_{stem}_{r['lang_code']}",
        )
    tab_idx += 1

    if r.get("subtitled_bytes"):
        with tabs[tab_idx]:
            st.video(r["subtitled_bytes"])
            st.download_button(
                f"⬇️ Download subtitled MP4",
                data=r["subtitled_bytes"],
                file_name=f"{stem}_dubbed_{r['lang_code']}_subtitled.mp4",
                mime="video/mp4",
                use_container_width=True,
                key=f"dl_sub_{stem}_{r['lang_code']}",
            )
        tab_idx += 1

    if r.get("audio_bytes"):
        with tabs[tab_idx]:
            st.audio(r["audio_bytes"])
            st.download_button(
                f"⬇️ Download Audio (.wav)",
                data=r["audio_bytes"],
                file_name=f"{stem}_dubbed_{r['lang_code']}.wav",
                mime="audio/wav",
                use_container_width=True,
                key=f"dl_aud_{stem}_{r['lang_code']}",
            )
        tab_idx += 1

    with tabs[tab_idx]:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📝 Source transcript**")
            st.markdown(
                f"<div class='tx-box'>{result.source_transcript}</div>",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(f"**🌐 {r['lang_name']} translation**")
            st.markdown(
                f"<div class='tx-box'>{result.translated_text}</div>",
                unsafe_allow_html=True,
            )
        if r.get("srt_content"):
            st.download_button(
                "💾 Download .srt subtitle file",
                data=r["srt_content"],
                file_name=f"{stem}_dubbed_{r['lang_code']}.srt",
                mime="text/plain",
                use_container_width=True,
                key=f"dl_srt_{stem}_{r['lang_code']}",
            )


def run_pipeline(input_path: str, selected: list, source_lang: str,
                 speaker: str, stem: str,
                 autofit: bool, burn_subs: bool, do_srt: bool, keep_bgm: bool,
                 bgm_volume: float, sub_font_size: int, sub_font_color: str, sub_bg_color: str,
                 sub_font_name: str, sub_position: str):
    from pipeline import dub_video

    with tempfile.TemporaryDirectory(prefix="sarvam_out_") as outdir:
        all_results = []
        progress    = st.progress(0, text="Starting…")

        for idx, lang_code in enumerate(selected):
            lang_name = SUPPORTED_LANGUAGES[lang_code]
            progress.progress(idx / len(selected), text=f"Dubbing → {lang_name}…")

            with st.status(f"**{lang_name}** ({lang_code})", expanded=True) as status:
                t0 = time.time()
                st.write("🎤 Saaras v3: transcribing…")
                try:
                    out_path = os.path.join(outdir, f"{stem}_dubbed_{lang_code}.mp4")
                    src = source_lang
                    if src == lang_code:
                        src = "en-IN" if lang_code != "en-IN" else "hi-IN"

                    result = dub_video(
                        video_path=input_path,
                        target_lang=lang_code,
                        source_lang=src,
                        speaker=speaker,
                        output_path=out_path,
                        autofit=autofit,
                        burn_subs=burn_subs,
                        export_srt=do_srt,
                        keep_bgm=keep_bgm,
                        bgm_volume=bgm_volume,
                        sub_font_size=sub_font_size,
                        sub_font_color=sub_font_color,
                        sub_bg_color=sub_bg_color,
                        sub_font_name=sub_font_name,
                        sub_position=sub_position,
                    )
                    elapsed = time.time() - t0

                    if autofit:
                        st.write("⏱️ Auto-fit: timing adjusted")
                    if result.srt_path:
                        st.write("💾 SRT: subtitle file exported")
                    if result.subtitled_video:
                        st.write("📝 Subtitles: burned onto video")
                    st.write(f"✅ Done in {elapsed:.0f}s")
                    status.update(label=f"✅ {lang_name} — {elapsed:.0f}s", state="complete")

                    with open(out_path, "rb") as vf:
                        video_bytes = vf.read()

                    subtitled_bytes = None
                    if result.subtitled_video and os.path.exists(result.subtitled_video):
                        with open(result.subtitled_video, "rb") as vf:
                            subtitled_bytes = vf.read()

                    audio_bytes = None
                    if result.audio_path and os.path.exists(result.audio_path):
                        with open(result.audio_path, "rb") as af:
                            audio_bytes = af.read()

                    srt_content = None
                    if result.srt_path and os.path.exists(result.srt_path):
                        with open(result.srt_path, "r", encoding="utf-8") as sf:
                            srt_content = sf.read()

                    # Copy to persistent output
                    persistent_dir = os.path.abspath("output")
                    os.makedirs(persistent_dir, exist_ok=True)
                    
                    final_video = result.subtitled_video or result.output_video
                    p_video = os.path.join(persistent_dir, os.path.basename(final_video)) if final_video else ""
                    if final_video and os.path.exists(final_video):
                        shutil.copy2(final_video, p_video)
                        
                    p_audio = os.path.join(persistent_dir, os.path.basename(result.audio_path)) if result.audio_path else ""
                    if result.audio_path and os.path.exists(result.audio_path):
                        shutil.copy2(result.audio_path, p_audio)
                        
                    p_srt = os.path.join(persistent_dir, os.path.basename(result.srt_path)) if result.srt_path else ""
                    if result.srt_path and os.path.exists(result.srt_path):
                        shutil.copy2(result.srt_path, p_srt)
                        
                    # Save to DB
                    db.save_job(
                        video_name=stem, 
                        source_lang=src, 
                        target_lang=lang_code, 
                        video_path=p_video, 
                        audio_path=p_audio, 
                        srt_path=p_srt
                    )

                    all_results.append({
                        "lang_code": lang_code, "lang_name": lang_name,
                        "result": result, "video_bytes": video_bytes,
                        "subtitled_bytes": subtitled_bytes,
                        "audio_bytes": audio_bytes,
                        "srt_content": srt_content,
                        "elapsed": elapsed,
                    })

                except Exception as e:
                    status.update(label=f"❌ {lang_name} failed", state="error")
                    st.exception(e)

        progress.progress(1.0, text="All done!")

        if not all_results:
            return

        st.markdown("---")
        st.markdown(f"### 🎉 {len(all_results)} dubbed video{'s' if len(all_results)>1 else ''} ready!")

        if len(all_results) == 1:
            show_result(all_results[0], stem)
        else:
            lang_tabs = st.tabs([r["lang_name"] for r in all_results])
            for tab, r in zip(lang_tabs, all_results):
                with tab:
                    st.caption(f"⏱ {r['elapsed']:.0f}s · {r['result'].segment_count} segments")
                    show_result(r, stem)

        # Side-by-side
        st.markdown("---")
        st.markdown("#### 🎬 Original vs Dubbed")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🎥 Original")
            st.video(input_path)
        with c2:
            first = all_results[0]
            cap = f"🎙️ {first['lang_name']}"
            if first.get("subtitled_bytes"):
                cap += " (with subtitles)"
            st.caption(cap)
            st.video(first.get("subtitled_bytes") or first["video_bytes"])


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_upload, tab_youtube, tab_live, tab_dashboard = st.tabs(["📁 Upload Video", "▶️ YouTube URL", "🎙️ Live Dubbing & Subtitles", "📊 Dashboard"])

# ── TAB 1: Upload ─────────────────────────────────────────────────────────────
with tab_upload:
    col_l, col_r = st.columns([1.1, 1], gap="large")
    with col_l:
        st.markdown("#### 📁 Upload video")
        uploaded = st.file_uploader(
            "Drop your video here",
            type=["mp4","mkv","mov","avi","webm"],
            label_visibility="collapsed", key="upload_file",
        )
        if uploaded:
            st.video(uploaded)
            st.caption(f"📄 `{uploaded.name}` · {uploaded.size/(1024*1024):.1f} MB")

        st.markdown("#### ✂️ Trim Video")
        trim_col1, trim_col2 = st.columns(2)
        with trim_col1: start_time = st.number_input("Start (s)", min_value=0, value=0, key="start_up")
        with trim_col2: end_time = st.number_input("End (s)", min_value=0, value=0, help="0 means till the end", key="end_up")

        selected_upload = language_selector("upload")
        st.markdown("")
        run_upload = st.button(
            f"🚀 Dub into {len(selected_upload)} language{'s' if len(selected_upload)!=1 else ''}",
            type="primary", use_container_width=True,
            disabled=not (uploaded and selected_upload and os.getenv("SARVAM_API_KEY")),
            key="btn_upload",
        )

    with col_r:
        st.markdown("#### 🎬 Output")
        if not uploaded:
            st.info("👈 Upload a video to get started")
        elif not os.getenv("SARVAM_API_KEY"):
            st.info("🔑 Add your Sarvam API key in the sidebar")
        elif not selected_upload:
            st.info("🌍 Select at least one target language")
        else:
            feats = []
            if do_autofit:   feats.append("⏱️ Auto-fit")
            if do_subtitles: feats.append("📝 Subtitles")
            if do_srt:       feats.append("💾 SRT")
            if do_bgm:       feats.append("🎵 BGM")
            st.success(
                f"Ready → **{', '.join(SUPPORTED_LANGUAGES[l] for l in selected_upload)}**  |  {' · '.join(feats)}",
                icon="✅",
            )

        if run_upload and uploaded and selected_upload and os.getenv("SARVAM_API_KEY"):
            with tempfile.NamedTemporaryFile(
                suffix=Path(uploaded.name).suffix, delete=False
            ) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name

            if start_time > 0 or end_time > 0:
                tmp_path = trim_video(tmp_path, start_time, end_time)

            try:
                run_pipeline(
                    tmp_path, selected_upload, source_lang, speaker,
                    Path(uploaded.name).stem,
                    autofit=do_autofit, burn_subs=do_subtitles, do_srt=do_srt, keep_bgm=do_bgm,
                    bgm_volume=bgm_volume, sub_font_size=sub_font_size, sub_font_color=sub_font_color,
                    sub_bg_color=sub_bg_color, sub_font_name=sub_font_name, sub_position=sub_position
                )
            finally:
                if os.path.exists(tmp_path): os.unlink(tmp_path)


# ── TAB 2: YouTube ────────────────────────────────────────────────────────────
with tab_youtube:
    col_l, col_r = st.columns([1.1, 1], gap="large")
    with col_l:
        st.markdown("#### ▶️ YouTube URL")
        yt_url = st.text_input(
            "Paste YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            label_visibility="collapsed", key="yt_url",
        )
        
        yt_res = st.selectbox("Resolution", ["360p", "480p", "720p", "1080p", "Best"], index=2)

        yt_valid    = False
        yt_video_id = None
        if yt_url:
            match = re.search(
                r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
                yt_url,
            )
            if match:
                yt_video_id = match.group(1)
                yt_valid    = True
                st.markdown(
                    f"<img src='https://img.youtube.com/vi/{yt_video_id}/hqdefault.jpg' "
                    f"style='width:100%;border-radius:10px;border:2px solid #e2e8f0;margin:8px 0'/>",
                    unsafe_allow_html=True,
                )
                st.caption(f"▶️ `{yt_url}`")
            else:
                st.warning("⚠️ Paste a valid YouTube URL")

        st.info("💡 **Tip:** Short clips (30–90s) work best.", icon="ℹ️")
        
        st.markdown("#### ✂️ Trim Video")
        yt_trim_col1, yt_trim_col2 = st.columns(2)
        with yt_trim_col1: yt_start_time = st.number_input("Start (s)", min_value=0, value=0, key="yt_start")
        with yt_trim_col2: yt_end_time = st.number_input("End (s)", min_value=0, value=0, help="0 means till the end", key="yt_end")

        selected_yt = language_selector("yt")
        st.markdown("")
        run_yt = st.button(
            f"🚀 Download & Dub into {len(selected_yt)} language{'s' if len(selected_yt)!=1 else ''}",
            type="primary", use_container_width=True,
            disabled=not (yt_valid and selected_yt and os.getenv("SARVAM_API_KEY")),
            key="btn_yt",
        )

    with col_r:
        st.markdown("#### 🎬 Output")
        if not yt_url:
            st.info("👈 Paste a YouTube URL to get started")
        elif not yt_valid:
            st.info("⚠️ Enter a valid YouTube URL")
        elif not os.getenv("SARVAM_API_KEY"):
            st.info("🔑 Add your Sarvam API key in the sidebar")
        elif not selected_yt:
            st.info("🌍 Select at least one target language")
        else:
            feats = []
            if do_autofit:   feats.append("⏱️ Auto-fit")
            if do_subtitles: feats.append("📝 Subtitles")
            if do_srt:       feats.append("💾 SRT")
            if do_bgm:       feats.append("🎵 BGM")
            st.success(
                f"Ready → **{', '.join(SUPPORTED_LANGUAGES[l] for l in selected_yt)}**  |  {' · '.join(feats)}",
                icon="✅",
            )

        if run_yt and yt_valid and selected_yt and os.getenv("SARVAM_API_KEY"):
            with tempfile.TemporaryDirectory(prefix="sarvam_yt_") as ytdir:
                yt_out = os.path.join(ytdir, "yt_video.mp4")

                with st.status("⬇️ Downloading from YouTube…", expanded=True) as dl_status:
                    st.write(f"Fetching: `{yt_url}`")
                    try:
                        import yt_dlp

                        yt_out = os.path.join(ytdir, "yt_video.mp4")
                        
                        if yt_res == "Best":
                            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                        else:
                            res_map = {"360p": 360, "480p": 480, "720p": 720, "1080p": 1080}
                            h = res_map[yt_res]
                            fmt = f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}][ext=mp4]/best"

                        ydl_opts = {
                            "format": fmt,
                            "outtmpl": yt_out,
                            "quiet": True,
                            "no_warnings": True,
                            "extractor_args": {
                                "youtube": {
                                    "player_client": ["android", "ios", "mweb", "web"],
                                }
                            },
                        }
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(yt_url, download=True)
                            yt_title = info.get("title", "YouTube Video")
                            yt_dur   = info.get("duration", 0)
                        dl_status.update(
                            label=f"✅ Downloaded: {yt_title[:50]} ({yt_dur}s)",
                            state="complete",
                        )
                        st.write(f"📹 **{yt_title}** · {yt_dur}s")

                    except Exception as e:
                        dl_status.update(label="❌ Download failed", state="error")
                        st.exception(e)
                        st.stop()

                st.markdown("**Original:**")
                st.video(yt_out)
                st.markdown("---")
                
                if yt_start_time > 0 or yt_end_time > 0:
                    yt_out = trim_video(yt_out, yt_start_time, yt_end_time)
                    
                safe_title = re.sub(r"[^\w\-]", "_", yt_title)[:40]
                run_pipeline(
                    yt_out, selected_yt, source_lang, speaker, safe_title,
                    autofit=do_autofit, burn_subs=do_subtitles, do_srt=do_srt, keep_bgm=do_bgm,
                    bgm_volume=bgm_volume, sub_font_size=sub_font_size, sub_font_color=sub_font_color,
                    sub_bg_color=sub_bg_color, sub_font_name=sub_font_name, sub_position=sub_position
                )

# ── TAB 3: Live Dubbing & Subtitles ──────────────────────────────────────────
with tab_live:
    import live_pipeline

    st.markdown("### 🎙️ Real-Time Live Dubbing & Live Subtitles")
    st.caption("Speak continuously into your microphone. Zivana streams audio to Sarvam Saaras Realtime STT, translates utterances instantly with Sarvam-Translate, and synthesizes live voice with Bulbul v3 streaming TTS.")

    if not os.getenv("SARVAM_API_KEY"):
        st.warning("⚠️ Please provide a valid SARVAM_API_KEY in the sidebar to start live dubbing.")
    else:
        # Settings Bar
        live_ctrl1, live_ctrl2, live_ctrl3, live_ctrl4 = st.columns([1.2, 1.2, 1, 1])

        with live_ctrl1:
            live_src_options = {"English (en-IN)": "en-IN"} | {
                f"{v} ({k})": k for k, v in live_pipeline.SUPPORTED_LANGUAGES.items() if k != "en-IN"
            }
            live_src_choice = st.selectbox(
                "Source Language",
                list(live_src_options.keys()),
                index=0,
                key="live_src_sel"
            )
            live_src_lang = live_src_options[live_src_choice]

        with live_ctrl2:
            live_tgt_options = {
                f"{v} ({k})": k for k, v in live_pipeline.SUPPORTED_LANGUAGES.items()
            }
            live_tgt_choice = st.selectbox(
                "Target Dubbing Language",
                list(live_tgt_options.keys()),
                index=0,  # Kannada
                key="live_tgt_sel"
            )
            live_target_lang = live_tgt_options[live_tgt_choice]

        with live_ctrl3:
            live_speaker_choice = st.selectbox(
                "Bulbul Voice",
                ["shubh", "anushka", "aditya", "priya", "rahul", "neha", "karun"],
                index=0,
                key="live_speaker_sel"
            )

        with live_ctrl4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            live_play_audio = st.toggle(
                "🔊 Voice Playback",
                value=True,
                help="Play dubbed voice through MacBook speakers in real time",
                key="live_play_audio_tog"
            )

        # Control Buttons
        btn_col1, btn_col2, _ = st.columns([1, 1, 2])
        current_session = st.session_state.get("live_session")
        is_session_active = bool(current_session and current_session.is_running)

        with btn_col1:
            if not is_session_active:
                if st.button("▶️ Start Live Dubbing", type="primary", use_container_width=True, key="btn_start_live"):
                    try:
                        sess = live_pipeline.LiveDubSession(
                            source_lang=live_src_lang,
                            target_lang=live_target_lang,
                            speaker=live_speaker_choice,
                            play_audio=live_play_audio,
                        )
                        sess.start()
                        st.session_state["live_session"] = sess
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Failed to start live session: {ex}")
            else:
                st.button("▶️ Running...", disabled=True, use_container_width=True, key="btn_running_live")

        with btn_col2:
            if is_session_active:
                if st.button("⏹️ Stop Session", type="secondary", use_container_width=True, key="btn_stop_live"):
                    if current_session:
                        current_session.stop()
                    st.session_state["live_session"] = None
                    st.rerun()
            else:
                st.button("⏹️ Stopped", disabled=True, use_container_width=True, key="btn_stopped_live")

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Live Real-time Fragment
        @st.fragment(run_every="0.5s")
        def render_live_teleprompter():
            active_sess = st.session_state.get("live_session")
            running = bool(active_sess and active_sess.is_running)

            if running:
                status_text = active_sess.status
                status_html = f"""
                <div class="live-status-pill">
                  <span class="live-pulse"></span>
                  <span>{status_text}</span>
                  <span style="margin-left: 12px; font-weight: 400; font-size: 0.78rem; opacity: 0.8;">
                    {live_src_lang} ➔ {live_target_lang} ({live_speaker_choice})
                  </span>
                </div>
                """
            else:
                status_html = """
                <div class="live-status-pill" style="border-color: #475569; color: #94a3b8;">
                  <span style="display:inline-block; width:8px; height:8px; background:#94a3b8; border-radius:50%; margin-right:8px;"></span>
                  <span>Session Idle — Click 'Start Live Dubbing' and speak into your microphone</span>
                </div>
                """
            st.markdown(status_html, unsafe_allow_html=True)

            partial_text = (active_sess.current_partial if (active_sess and active_sess.current_partial) else "Listening for speech...")
            translated_text = (active_sess.current_translated if (active_sess and active_sess.current_translated) else "Translated subtitles will appear here in real-time...")

            col_sub_src, col_sub_tgt = st.columns(2, gap="medium")

            with col_sub_src:
                st.markdown(f"""
                <div class="teleprompter-card">
                  <div class="teleprompter-title" style="color: #64748b;">
                    <span>🎙️ Live Transcription (Source)</span>
                    <span style="background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">{live_src_lang}</span>
                  </div>
                  <div class="teleprompter-text" style="color: #0f172a;">
                    {partial_text}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with col_sub_tgt:
                st.markdown(f"""
                <div class="teleprompter-target">
                  <div class="teleprompter-title" style="color: #a5f3fc;">
                    <span>🔊 Live Dubbed Subtitle (Target)</span>
                    <span style="background: rgba(255,255,255,0.2); color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">{live_target_lang}</span>
                  </div>
                  <div class="teleprompter-text">
                    {translated_text}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            subs = active_sess.subtitles if active_sess else []
            if subs:
                st.markdown(f"#### 📜 Live Subtitle Stream ({len(subs)} utterances)")
                items_html = []
                for s in reversed(subs[-10:]):
                    items_html.append(f"""
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                      <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748b; margin-bottom: 4px;">
                        <span>⏱️ {s.timestamp}</span>
                        <span>#{s.index}</span>
                      </div>
                      <div style="font-size: 0.88rem; color: #475569; margin-bottom: 4px;"><b>Original:</b> {s.source_text}</div>
                      <div style="font-size: 1rem; color: #0891b2; font-weight: 600;"><b>Dubbed:</b> {s.translated_text}</div>
                    </div>
                    """)
                st.markdown(f'<div class="sub-history-box">{"".join(items_html)}</div>', unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    st.download_button(
                        "💾 Download Live Subtitles (.srt)",
                        data=active_sess.export_srt(),
                        file_name=f"live_dubbing_{live_target_lang}.srt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_live_srt_{len(subs)}"
                    )
                with exp_col2:
                    st.download_button(
                        "📄 Download Session Log (.txt)",
                        data=active_sess.export_text(),
                        file_name=f"live_transcript_{live_target_lang}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_live_txt_{len(subs)}"
                    )

        render_live_teleprompter()

# ── TAB 4: Dashboard ──────────────────────────────────────────────────────────
with tab_dashboard:
    st.markdown("#### 📊 Processing History")
    history = db.get_history()
    
    if not history:
        st.info("No videos have been dubbed yet. Your history will appear here.")
    else:
        for job in history:
            with st.expander(f"🎬 {job['video_name']} ({job['source_lang']} → {job['target_lang']}) - {job['timestamp']}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    if job['video_path'] and os.path.exists(job['video_path']):
                        st.video(job['video_path'])
                        with open(job['video_path'], "rb") as f:
                            st.download_button("⬇️ Download Video", data=f.read(), file_name=os.path.basename(job['video_path']), mime="video/mp4", key=f"dl_v_{job['id']}")
                    else:
                        st.warning("Video file not found.")
                with col2:
                    if job['audio_path'] and os.path.exists(job['audio_path']):
                        st.audio(job['audio_path'])
                        with open(job['audio_path'], "rb") as f:
                            st.download_button("⬇️ Download Audio", data=f.read(), file_name=os.path.basename(job['audio_path']), mime="audio/wav", key=f"dl_a_{job['id']}")
                    
                    if job['srt_path'] and os.path.exists(job['srt_path']):
                        with open(job['srt_path'], "rb") as f:
                            st.download_button("⬇️ Download Subtitles", data=f.read(), file_name=os.path.basename(job['srt_path']), mime="text/plain", key=f"dl_s_{job['id']}")
