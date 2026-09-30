import os
import time
import tempfile
import streamlit as st
from dotenv import load_dotenv

# Import pipeline helpers
from main import run_pipeline
from core.RAG import ask_question

load_dotenv()

# Set Streamlit Page Config
st.set_page_config(
    page_title="MeetMind • Meeting & Call Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Modern Styling (Glassmorphism & Dark Aesthetic)
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Main background & glass styling */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(20, 24, 40, 1) 0%, rgba(10, 12, 22, 1) 90.2%);
        color: #f1f5f9;
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #ffffff;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    /* Hero Banner */
    .hero-container {
        padding: 24px 30px;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        backdrop-filter: blur(12px);
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.18);
        border: 1px solid rgba(99, 102, 241, 0.4);
        color: #a5b4fc;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(120deg, #ffffff 30%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 6px;
        max-width: 750px;
    }

    /* Glass Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        backdrop-filter: blur(8px);
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .card-header.summary { color: #38bdf8; }
    .card-header.actions { color: #4ade80; }
    .card-header.decisions { color: #facc15; }
    .card-header.questions { color: #f472b6; }

    /* Preformatted Code & Transcript */
    .transcript-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        color: #cbd5e1;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.88rem;
        line-height: 1.6;
        max-height: 480px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    /* Primary Buttons */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: #ffffff;
        font-weight: 600;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1.4rem;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
    }

    /* Chat Messages */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# Sidebar Controls
with st.sidebar:
    st.markdown("### 🎙️ Source Input")
    st.caption("Upload call recording, meeting audio/video, or provide a YouTube link.")
    
    input_mode = st.radio(
        "Input Type",
        ["YouTube URL", "Upload Audio/Video", "Use Sample Recording"],
        index=0
    )
    
    source_target = None
    
    if input_mode == "YouTube URL":
        source_target = st.text_input(
            "YouTube Video URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Pastes direct YouTube link for automatic extraction."
        )
    elif input_mode == "Upload Audio/Video":
        uploaded_file = st.file_uploader(
            "Upload File",
            type=["mp3", "wav", "m4a", "webm", "mp4", "mkv", "aac", "ogg"],
            help="Upload meeting or call recordings."
        )
        if uploaded_file is not None:
            # Save to temporary file
            suffix = os.path.splitext(uploaded_file.name)[-1]
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"meetmind_{int(time.time())}{suffix}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            source_target = temp_path
            st.success(f"Loaded: {uploaded_file.name}")
    else:
        sample_file = "English Speech ｜ English Speaking Practice ｜ English Subtitles [pjhx3e8ZbKs].webm"
        if os.path.exists(sample_file):
            st.info(f"Sample available: `{sample_file}`")
            source_target = sample_file
        else:
            st.warning("Sample recording file not detected in workspace.")
            
    language = st.selectbox(
        "Audio Spoken Language",
        ["english", "hinglish"],
        index=0,
        help="Choose Hinglish if speech mixes Hindi & English for automated translation."
    )
    
    st.markdown("---")
    
    # Process Button
    start_btn = st.button("🚀 Analyze Recording", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ⚙️ Engine Telemetry")
    api_key = os.getenv("NVIDIA_API_KEY")
    st.markdown(f"- **LLM Provider:** `NVIDIA NIM / GPT-OSS`")
    st.markdown(f"- **Key Configured:** {'🟢 Connected' if api_key else '🔴 Missing Key'}")
    st.markdown("- **ASR Engine:** `Whisper (Local PyTorch)`")
    st.markdown("- **Vector Store:** `ChromaDB + HuggingFace`")
    
    if st.session_state.pipeline_result:
        if st.button("🔄 Clear Analysis", use_container_width=True):
            st.session_state.pipeline_result = None
            st.session_state.chat_history = []
            st.rerun()

# Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">⚡ AI Assistant</div>
    <h1 class="hero-title">MeetMind</h1>
    <div class="hero-subtitle">Simple, smart meeting and call notes. Turn recordings into clean summaries, action items, and answers.</div>
</div>
""", unsafe_allow_html=True)

# Processing Trigger
if start_btn:
    if not source_target:
        st.error("Please supply a valid YouTube link, upload an audio/video file, or select a sample recording.")
    else:
        st.session_state.is_processing = True
        progress_placeholder = st.empty()
        
        with progress_placeholder.container():
            with st.spinner("Processing audio extraction, transcription, and intelligence pipeline..."):
                try:
                    result = run_pipeline(source_target, language=language)
                    st.session_state.pipeline_result = result
                    st.session_state.chat_history = []
                    st.success("Analysis and vector embedding completed successfully!")
                except Exception as e:
                    st.error(f"Pipeline execution encountered an error: {str(e)}")
        progress_placeholder.empty()

# Render Results Dashboard
res = st.session_state.pipeline_result

if res:
    # Title & Metadata Banner
    st.markdown(f"### 📌 {res.get('title', 'Meeting Analysis')}")
    
    # Tabs layout
    tab_intel, tab_chat, tab_transcript, tab_export = st.tabs([
        "📊 Executive Intelligence",
        "💬 Chat with Audio (RAG)",
        "📝 Full Transcript",
        "📥 Export & Share"
    ])
    
    with tab_intel:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("""
            <div class="glass-card">
                <div class="card-header summary">📋 Executive Summary</div>
            """, unsafe_allow_html=True)
            st.write(res.get("summary", "No summary generated."))
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("""
            <div class="glass-card">
                <div class="card-header decisions">🔑 Key Decisions</div>
            """, unsafe_allow_html=True)
            st.write(res.get("key_decisions", "No decisions extracted."))
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="glass-card">
                <div class="card-header actions">✅ Action Items & Deliverables</div>
            """, unsafe_allow_html=True)
            st.write(res.get("action_items", "No action items extracted."))
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("""
            <div class="glass-card">
                <div class="card-header questions">❓ Open Questions & Risks</div>
            """, unsafe_allow_html=True)
            st.write(res.get("open_questions", "No questions identified."))
            st.markdown("</div>", unsafe_allow_html=True)

    with tab_chat:
        st.markdown("#### 💬 Ask Questions About the Recording")
        st.caption("Answers are strictly grounded in the meeting context using ChromaDB vector search.")
        
        # Suggested questions chips
        chip_col1, chip_col2, chip_col3 = st.columns(3)
        sample_prompt = None
        if chip_col1.button("📌 Summarize key takeaways"):
            sample_prompt = "Summarize the primary takeaways and main points."
        if chip_col2.button("🎯 What are the action items?"):
            sample_prompt = "List all key action items, owners, or tasks mentioned."
        if chip_col3.button("❓ What was left unresolved?"):
            sample_prompt = "What questions, unresolved problems, or doubts were raised?"

        # Display conversation history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # User prompt input
        user_query = st.chat_input("Ask anything about this recording...") or sample_prompt
        
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.write(user_query)
            
            with st.chat_message("assistant"):
                with st.spinner("Retrieving from context..."):
                    try:
                        rag_chain = res.get("rag_chain")
                        if rag_chain:
                            answer = ask_question(rag_chain, user_query)
                        else:
                            answer = "RAG chain unavailable."
                    except Exception as err:
                        answer = f"Error answering question: {err}"
                    st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

    with tab_transcript:
        st.markdown("#### 📜 Verbatim Transcript")
        search_term = st.text_input("🔍 Search transcript for keyword", placeholder="Type word or phrase...")
        transcript_text = res.get("transcript", "")
        
        if search_term:
            highlighted = transcript_text.replace(search_term, f"**_{search_term}_**")
            st.markdown(f'<div class="transcript-box">{highlighted}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="transcript-box">{transcript_text}</div>', unsafe_allow_html=True)
            
        st.download_button(
            label="📄 Download Transcript (.txt)",
            data=transcript_text,
            file_name=f"transcript_{int(time.time())}.txt",
            mime="text/plain"
        )

    with tab_export:
        st.markdown("#### 📥 Export Meeting Brief")
        brief_markdown = f"""# {res.get('title', 'Meeting Brief')}
*Generated via MeetMind*

## 📋 Executive Summary
{res.get('summary', '')}

## 🔑 Key Decisions
{res.get('key_decisions', '')}

## ✅ Action Items
{res.get('action_items', '')}

## ❓ Open Questions
{res.get('open_questions', '')}

---
### Transcript Excerpt
{res.get('transcript', '')[:1000]}...
"""
        st.download_button(
            label="📥 Download Comprehensive Report (.md)",
            data=brief_markdown,
            file_name=f"MeetMind_Report_{int(time.time())}.md",
            mime="text/markdown"
        )
else:
    # Empty State placeholder
    st.info("👈 Choose an input source in the sidebar (YouTube URL, audio/video upload, or sample) and click **Analyze Recording** to get started.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="glass-card">
            <h4>🎙️ Multilingual Speech Ingestion</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">Processes YouTube streams, MP3s, WAVs, and video files with Whisper AI. Supports English & Hinglish.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="glass-card">
            <h4>🧠 Automated Structured Synthesis</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">Extracts executive summaries, key decisions, actionable deliverables, and open questions automatically.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="glass-card">
            <h4>💬 Grounded RAG Conversation</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">Chat with your audio recording via ChromaDB vector embeddings with zero hallucinations.</p>
        </div>
        """, unsafe_allow_html=True)
