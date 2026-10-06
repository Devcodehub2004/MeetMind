import os
import time
import tempfile
import html
import streamlit as st
from dotenv import load_dotenv

from main import run_pipeline
from core.RAG import ask_question

load_dotenv()

st.set_page_config(
    page_title="MeetMind AI • Meeting Intelligence",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- State ----------
defaults = {
    "pipeline_result": None,
    "chat_history": [],
    "is_processing": False,
    "input_mode": "YouTube URL",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- Design system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap');

:root {
  --bg:#070A12;
  --surface:#0D1220;
  --surface2:#111827;
  --line:rgba(255,255,255,.09);
  --muted:#8B98AE;
  --text:#F7F9FC;
  --blue:#6EA8FE;
  --violet:#9B87F5;
  --cyan:#63E6FF;
}

html, body, [class*="css"] { font-family:Inter,sans-serif; }
.stApp {
  color:var(--text);
  background:
    radial-gradient(900px 480px at 50% -80px, rgba(91,108,255,.20), transparent 60%),
    radial-gradient(600px 350px at 88% 22%, rgba(99,230,255,.08), transparent 60%),
    var(--bg);
}
[data-testid="stHeader"] { background:transparent; }
[data-testid="stToolbar"] { right:1rem; }
.block-container { max-width:1180px; padding-top:1.4rem; padding-bottom:5rem; }
#MainMenu, footer { visibility:hidden; }

.mm-nav {
 display:flex; align-items:center; justify-content:space-between;
 padding:12px 16px; border:1px solid var(--line); border-radius:18px;
 background:rgba(13,18,32,.72); backdrop-filter:blur(18px);
 box-shadow:0 16px 50px rgba(0,0,0,.22); margin-bottom:58px;
}
.mm-brand { display:flex; align-items:center; gap:10px; font:800 17px Manrope,sans-serif; }
.mm-logo {
 width:31px;height:31px;border-radius:10px;display:grid;place-items:center;
 background:linear-gradient(135deg,#7C8CFF,#8D5CFF); box-shadow:0 0 25px rgba(124,140,255,.3);
}
.mm-live { display:flex;align-items:center;gap:8px;color:#A9B4C7;font-size:12px;font-weight:600; }
.mm-dot { width:7px;height:7px;border-radius:50%;background:#4ADE80;box-shadow:0 0 12px #4ADE80; }

.hero { text-align:center; max-width:900px; margin:0 auto 34px; }
.eyebrow {
 display:inline-flex; gap:8px; align-items:center; border:1px solid rgba(139,135,245,.3);
 background:rgba(139,135,245,.08); color:#C8C1FF; padding:7px 12px; border-radius:999px;
 font-size:12px; font-weight:700; letter-spacing:.04em; margin-bottom:20px;
}
.hero h1 {
 font:800 clamp(2.8rem,7vw,5.6rem)/.98 Manrope,sans-serif; letter-spacing:-.065em;
 margin:0; color:white;
}
.gradient-word {
 background:linear-gradient(90deg,#8DBBFF 10%,#A78BFA 52%,#72E6FF);
 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.hero p { max-width:690px;margin:22px auto 0;color:#98A5BA;font-size:17px;line-height:1.7; }

.workspace {
 margin:34px auto 20px; padding:24px; border-radius:24px; border:1px solid rgba(255,255,255,.10);
 background:linear-gradient(180deg,rgba(17,24,39,.88),rgba(10,14,25,.92));
 box-shadow:0 30px 90px rgba(0,0,0,.35), inset 0 1px rgba(255,255,255,.04);
 position:relative; overflow:hidden;
}
.workspace:before {
 content:"";position:absolute;width:380px;height:160px;left:30%;top:-130px;
 background:#786CFF;filter:blur(90px);opacity:.17;pointer-events:none;
}
.section-label { color:#E8EDF7;font:700 14px Manrope,sans-serif;margin-bottom:4px; }
.section-help { color:#78869D;font-size:12px;margin-bottom:14px; }

div[data-testid="stRadio"] > label { display:none; }
div[data-testid="stRadio"] [role="radiogroup"] { gap:10px; }
div[data-testid="stRadio"] label {
 background:#0A0F1B !important;border:1px solid var(--line) !important;border-radius:13px !important;
 padding:10px 14px !important; transition:.2s ease;
}
div[data-testid="stRadio"] label:hover { border-color:rgba(124,140,255,.6)!important; transform:translateY(-1px); }

div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
 background:#080D17!important;border-color:var(--line)!important;border-radius:13px!important;
}
[data-testid="stFileUploaderDropzone"] {
 background:#080D17!important;border:1px dashed rgba(124,140,255,.35)!important;border-radius:16px!important;
}
div.stButton > button, div.stDownloadButton > button {
 border-radius:13px; border:1px solid rgba(255,255,255,.10);
 min-height:46px; font-weight:700; transition:.2s ease;
}
div.stButton > button[kind="primary"] {
 color:white;border:0;
 background:linear-gradient(110deg,#6478FF,#8B5CF6 58%,#3DB8E8);
 box-shadow:0 10px 30px rgba(99,102,241,.24);
}
div.stButton > button:hover, div.stDownloadButton > button:hover { transform:translateY(-2px); }

.pipeline {
 display:flex;justify-content:center;align-items:center;gap:9px;flex-wrap:wrap;
 margin:22px 0 2px;color:#728198;font-size:11px;font-weight:700;
}
.pipe-pill {padding:6px 10px;border:1px solid var(--line);border-radius:999px;background:#090E18;}
.pipe-arrow {color:#475569;}

.features {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:22px;}
.feature {
 min-width:0;padding:20px;border:1px solid var(--line);border-radius:18px;
 background:rgba(13,18,32,.58); transition:.25s ease;
}
.feature:hover {transform:translateY(-3px);border-color:rgba(124,140,255,.34);background:rgba(17,24,39,.75);}
.feature-icon {
 width:38px;height:38px;border-radius:11px;display:grid;place-items:center;margin-bottom:22px;
 background:linear-gradient(145deg,rgba(110,168,254,.16),rgba(155,135,245,.14));font-size:18px;
}
.feature h3 {font:700 16px Manrope,sans-serif;margin:0 0 8px;color:#F5F7FB;}
.feature p {color:#7F8DA3;font-size:12.5px;line-height:1.65;margin:0;}

.result-head {margin:42px 0 20px;}
.result-head h2 {font:800 30px Manrope,sans-serif;margin:0 0 6px;}
.result-head p {color:#8190A7;margin:0;}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
 gap:8px;background:#0A0F19;padding:6px;border:1px solid var(--line);border-radius:15px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {border-radius:10px;padding:10px 16px;}
[data-testid="stTabs"] [aria-selected="true"] {background:#171E2D;}

.insight {
 height:100%;padding:21px;border:1px solid var(--line);border-radius:18px;
 background:linear-gradient(145deg,rgba(17,24,39,.8),rgba(10,15,27,.82));margin-bottom:14px;
}
.insight-top {display:flex;align-items:center;gap:9px;color:#F3F6FB;font-weight:800;margin-bottom:13px;}
.insight p {color:#A2AEC0;line-height:1.7;margin:0;}
.transcript {
 background:#080D17;border:1px solid var(--line);border-radius:17px;padding:20px;
 color:#B7C1D0;font-family:'SFMono-Regular',Consolas,monospace;font-size:13px;line-height:1.7;
 max-height:560px;overflow:auto;white-space:pre-wrap;
}
.empty {
 text-align:center;padding:22px;color:#75839A;font-size:13px;
}
.stChatMessage {border:1px solid var(--line);background:rgba(13,18,32,.55);border-radius:16px;}
[data-testid="stAlert"] {border-radius:14px;}

@media(max-width:850px){
 .block-container{padding-left:1rem;padding-right:1rem}
 .mm-nav{margin-bottom:38px}
 .hero h1{font-size:3.2rem}
 .features{grid-template-columns:1fr}
 .workspace{padding:16px}
}
</style>
""", unsafe_allow_html=True)

# ---------- Top nav ----------
api_key = os.getenv("NVIDIA_API_KEY")
st.markdown(f"""
<div class="mm-nav">
  <div class="mm-brand"><div class="mm-logo">✦</div> MeetMind <span style="color:#718096;font-weight:600">AI</span></div>
  <div class="mm-live"><span class="mm-dot"></span>{'AI engine online' if api_key else 'Interface online • API key required'}</div>
</div>
""", unsafe_allow_html=True)

# ---------- Hero ----------
st.markdown("""
<section class="hero">
  <div class="eyebrow">✦ AI MEETING INTELLIGENCE</div>
  <h1>Your meetings,<br><span class="gradient-word">finally useful.</span></h1>
  <p>Turn recordings into clear decisions, action items and searchable knowledge.
  MeetMind transcribes, understands and lets you talk to every conversation.</p>
</section>
""", unsafe_allow_html=True)

# ---------- Input workspace ----------
st.markdown('<div class="workspace">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Analyze a meeting</div><div class="section-help">Choose a source and MeetMind will handle the rest.</div>', unsafe_allow_html=True)

input_mode = st.radio(
    "Input type",
    ["YouTube URL", "Upload Audio/Video", "Use Sample Recording"],
    horizontal=True,
    label_visibility="collapsed",
)

source_target = None
language_col, status_col = st.columns([1, 1])

if input_mode == "YouTube URL":
    source_target = st.text_input(
        "YouTube URL",
        placeholder="Paste a YouTube meeting, interview or call URL…",
        label_visibility="collapsed",
    )
elif input_mode == "Upload Audio/Video":
    uploaded_file = st.file_uploader(
        "Drop your meeting here",
        type=["mp3", "wav", "m4a", "webm", "mp4", "mkv", "aac", "ogg"],
        help="MP3, WAV, M4A, WEBM, MP4, MKV, AAC or OGG",
    )
    if uploaded_file is not None:
        suffix = os.path.splitext(uploaded_file.name)[-1]
        temp_path = os.path.join(tempfile.gettempdir(), f"meetmind_{int(time.time())}{suffix}")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        source_target = temp_path
        st.success(f"Ready: {uploaded_file.name}")
else:
    sample_file = "English Speech ｜ English Speaking Practice ｜ English Subtitles [pjhx3e8ZbKs].webm"
    if os.path.exists(sample_file):
        source_target = sample_file
        st.success("Sample recording is ready.")
    else:
        st.warning("Sample recording is not available in this deployment.")

with language_col:
    language = st.selectbox(
        "Spoken language",
        ["english", "hinglish"],
        help="Choose Hinglish when the recording mixes Hindi and English.",
    )
with status_col:
    st.markdown(
        f"<div style='padding-top:30px;color:#7F8DA3;font-size:12px'>"
        f"{'● NVIDIA NIM connected' if api_key else '○ NVIDIA_API_KEY not detected'}</div>",
        unsafe_allow_html=True,
    )

start_btn = st.button("✦ Analyze with MeetMind  →", type="primary", use_container_width=True)

st.markdown("""
<div class="pipeline">
 <span class="pipe-pill">Audio</span><span class="pipe-arrow">→</span>
 <span class="pipe-pill">Whisper</span><span class="pipe-arrow">→</span>
 <span class="pipe-pill">Intelligence</span><span class="pipe-arrow">→</span>
 <span class="pipe-pill">Vector Memory</span><span class="pipe-arrow">→</span>
 <span class="pipe-pill">RAG Chat</span>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ---------- Run pipeline ----------
if start_btn:
    if not source_target:
        st.error("Add a YouTube URL, upload a recording, or choose the sample first.")
    else:
        st.session_state.is_processing = True
        try:
            with st.status("MeetMind is understanding your recording…", expanded=True) as status:
                st.write("Preparing audio source…")
                result = run_pipeline(source_target, language=language)
                st.write("Building meeting intelligence and searchable memory…")
                st.session_state.pipeline_result = result
                st.session_state.chat_history = []
                status.update(label="Meeting intelligence ready", state="complete", expanded=False)
        except Exception as e:
            st.error(f"Pipeline error: {e}")
        finally:
            st.session_state.is_processing = False

res = st.session_state.pipeline_result

# ---------- Empty state ----------
if not res:
    st.markdown("""
    <div class="features">
      <div class="feature">
        <div class="feature-icon">◉</div>
        <h3>Understand every word</h3>
        <p>Whisper turns meetings, calls and videos into accurate searchable transcripts with English and Hinglish support.</p>
      </div>
      <div class="feature">
        <div class="feature-icon">✦</div>
        <h3>Find what matters</h3>
        <p>Automatically surface summaries, decisions, action items and unresolved questions instead of rereading notes.</p>
      </div>
      <div class="feature">
        <div class="feature-icon">⌁</div>
        <h3>Ask the conversation</h3>
        <p>Use grounded RAG to ask follow-up questions and retrieve answers directly from the meeting context.</p>
      </div>
    </div>
    <div class="empty">One recording in. Decisions, tasks and searchable knowledge out.</div>
    """, unsafe_allow_html=True)

# ---------- Results ----------
else:
    title = html.escape(str(res.get("title", "Meeting Analysis")))
    st.markdown(
        f'<div class="result-head"><h2>{title}</h2>'
        '<p>Your conversation has been transformed into structured, searchable intelligence.</p></div>',
        unsafe_allow_html=True,
    )

    tab_intel, tab_chat, tab_transcript, tab_export = st.tabs(
        ["✦ Intelligence", "⌁ Ask MeetMind", "≡ Transcript", "↓ Export"]
    )

    with tab_intel:
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="insight"><div class="insight-top">◫ Executive Summary</div>', unsafe_allow_html=True)
            st.write(res.get("summary", "No summary generated."))
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="insight"><div class="insight-top">◆ Key Decisions</div>', unsafe_allow_html=True)
            st.write(res.get("key_decisions", "No decisions extracted."))
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="insight"><div class="insight-top">✓ Action Items</div>', unsafe_allow_html=True)
            st.write(res.get("action_items", "No action items extracted."))
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="insight"><div class="insight-top">△ Open Questions & Risks</div>', unsafe_allow_html=True)
            st.write(res.get("open_questions", "No open questions identified."))
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_chat:
        st.markdown("### Ask anything about this meeting")
        st.caption("Answers are grounded in the indexed recording context.")

        c1, c2, c3 = st.columns(3)
        sample_prompt = None
        if c1.button("Key takeaways", use_container_width=True):
            sample_prompt = "Summarize the primary takeaways and main points."
        if c2.button("Action items", use_container_width=True):
            sample_prompt = "List all key action items, owners, or tasks mentioned."
        if c3.button("Unresolved issues", use_container_width=True):
            sample_prompt = "What questions, unresolved problems, or doubts were raised?"

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_query = st.chat_input("Ask MeetMind about this recording…") or sample_prompt
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.write(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Searching meeting memory…"):
                    try:
                        rag_chain = res.get("rag_chain")
                        answer = ask_question(rag_chain, user_query) if rag_chain else "RAG chain unavailable."
                    except Exception as err:
                        answer = f"Error answering question: {err}"
                    st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

    with tab_transcript:
        st.markdown("### Full transcript")
        search_term = st.text_input("Search transcript", placeholder="Search for a word or phrase…")
        transcript_text = str(res.get("transcript", ""))

        safe_transcript = html.escape(transcript_text)
        if search_term:
            # Safe, case-preserving highlight.
            safe_term = html.escape(search_term)
            safe_transcript = safe_transcript.replace(
                safe_term, f"<mark style='background:#6658C7;color:white;padding:1px 3px;border-radius:4px'>{safe_term}</mark>"
            )

        st.markdown(f'<div class="transcript">{safe_transcript}</div>', unsafe_allow_html=True)
        st.download_button(
            "↓ Download transcript",
            data=transcript_text,
            file_name=f"transcript_{int(time.time())}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with tab_export:
        st.markdown("### Take MeetMind with you")
        st.caption("Export a clean Markdown brief containing the meeting intelligence and transcript excerpt.")

        brief_markdown = f"""# {res.get('title', 'Meeting Brief')}
*Generated by MeetMind AI*

## Executive Summary
{res.get('summary', '')}

## Key Decisions
{res.get('key_decisions', '')}

## Action Items
{res.get('action_items', '')}

## Open Questions
{res.get('open_questions', '')}

---

## Transcript Excerpt
{str(res.get('transcript', ''))[:1000]}...
"""
        st.download_button(
            "↓ Download meeting brief (.md)",
            data=brief_markdown,
            file_name=f"MeetMind_Report_{int(time.time())}.md",
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )

        if st.button("Clear this analysis", use_container_width=True):
            st.session_state.pipeline_result = None
            st.session_state.chat_history = []
            st.rerun()
