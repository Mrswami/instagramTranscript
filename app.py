import streamlit as st
import os
import json
from pathlib import Path
from transcriber import InstagramTranscriber

# Page configuration
st.set_page_config(
    page_title="Instagram Reel & Post Transcriber",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism CSS Styling
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Card Container */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Hero Header */
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 24px;
    }

    /* Custom Input Fields */
    .stTextInput > div > div > input {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(139, 92, 246, 0.4) !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #ec4899 !important;
        box-shadow: 0 0 12px rgba(236, 72, 153, 0.4) !important;
    }

    /* Custom Transmute Button */
    .stButton > button {
        background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        border: none !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4) !important;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.6) !important;
    }

    /* Transcript Box */
    .transcript-box {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        padding: 20px;
        color: #f1f5f9;
        font-size: 1.05rem;
        line-height: 1.6;
        max-height: 350px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    /* Badge Tags */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        background: rgba(139, 92, 246, 0.2);
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.3);
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Transcriber
output_dir = Path("output")
transcriber = InstagramTranscriber(output_dir=output_dir)

# Header Section
st.markdown('<div class="hero-title">🎙️ Instagram Reel & Post Transcriber</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Convert any Instagram Reel or Post video/audio link into high-quality MP3 audio & detailed copyable text transcripts.</div>', unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("### ⚙️ Engine Settings")
model_choice = st.sidebar.selectbox(
    "Whisper Model Speed & Accuracy:",
    options=["tiny", "base", "small", "medium"],
    index=1,
    help="Tiny is fastest; Base is recommended for general use; Small/Medium offer higher accuracy."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 💡 How to use:
1. Copy any Instagram Reel or Post link.
2. Paste link in the input box.
3. Click **Transmute to Transcript**.
4. Listen to preview MP3 & click **Copy Transcript**.
5. Download TXT, SRT, VTT, or JSON subtitle files.
""")

# Main Input Section
with st.container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        insta_url = st.text_input(
            "Instagram Reel / Post URL:",
            placeholder="https://www.instagram.com/reel/Cxxxxxx/ or https://www.instagram.com/p/Cxxxxxx/",
            key="url_input"
        )
    with col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        transmute_btn = st.button("✨ Transmute Link")
        
    st.markdown('</div>', unsafe_allow_html=True)

# Process Trigger
if transmute_btn:
    if not insta_url.strip():
        st.error("⚠️ Please enter a valid Instagram URL.")
    elif not transcriber.validate_url(insta_url):
        st.error("⚠️ Invalid URL format. Make sure it contains instagram.com/reel/ or instagram.com/p/.")
    else:
        with st.status("🚀 Processing Instagram Media...", expanded=True) as status:
            try:
                st.write("📥 Step 1/3: Extracting audio from Instagram URL...")
                audio_path = transcriber.download_audio(insta_url)
                st.write(f"✅ Audio downloaded and converted to MP3: `{audio_path.name}`")

                st.write(f"🧠 Step 2/3: Running Speech-to-Text Whisper AI ({model_choice} model)...")
                result_data = transcriber.process_url(insta_url, model_name=model_choice)
                st.write("✅ Transcript generated successfully!")

                status.update(label="🎉 Processing Complete!", state="complete", expanded=False)
                st.session_state['result'] = result_data

            except Exception as e:
                status.update(label="❌ Error occurred!", state="error", expanded=True)
                st.error(f"Error details: {str(e)}")

# Display Results Section
if 'result' in st.session_state:
    res = st.session_state['result']

    st.markdown("---")
    st.markdown("### 📊 Transcribed Results & Media")

    res_col1, res_col2 = st.columns([2, 1])

    with res_col1:
        st.markdown('<span class="badge">Full Transcript</span>', unsafe_allow_html=True)
        st.markdown(f'<div class="transcript-box">{res["text"]}</div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        # Copy to Clipboard code snippet widget (built-in copy button)
        st.text_area("📋 Copyable Raw Text", value=res["text"], height=100, help="Click top right corner icon of this box to copy!")

    with res_col2:
        st.markdown('<span class="badge">Audio Preview</span>', unsafe_allow_html=True)
        if os.path.exists(res["audio_file"]):
            with open(res["audio_file"], "rb") as f:
                audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")

            st.download_button(
                label="🎵 Download MP3",
                data=audio_bytes,
                file_name=os.path.basename(res["audio_file"]),
                mime="audio/mp3",
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("#### 📥 Export Subtitles & Captions")
        
        st.download_button(
            label="📄 Export as TXT",
            data=res["text"],
            file_name="transcript.txt",
            mime="text/plain",
            use_container_width=True
        )
        st.download_button(
            label="🎬 Export SRT (Subtitles)",
            data=res["srt"],
            file_name="transcript.srt",
            mime="text/plain",
            use_container_width=True
        )
        st.download_button(
            label="🌐 Export WebVTT (.vtt)",
            data=res["vtt"],
            file_name="transcript.vtt",
            mime="text/vtt",
            use_container_width=True
        )
        st.download_button(
            label="📌 Export JSON Data",
            data=res["json"],
            file_name="transcript.json",
            mime="application/json",
            use_container_width=True
        )

    # Detailed Timestamped Segments Table
    st.markdown("---")
    st.markdown("### ⏱️ Timestamp Breakdown")
    with st.expander("View line-by-line timestamp segments", expanded=False):
        for seg in res.get("segments", []):
            start_str = transcriber.format_timestamp(seg['start'])
            end_str = transcriber.format_timestamp(seg['end'])
            st.markdown(f"**[{start_str} ➡️ {end_str}]** : {seg['text']}")
