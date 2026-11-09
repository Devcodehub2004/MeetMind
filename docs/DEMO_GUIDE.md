# MeetMind — recruiter demo runbook

> **Status:** A capture script for a local run, **not** a verified video, performance measurement or public deployment. Do not add screenshots until a real run succeeds.

## Before running

- Install Python 3.10–3.12, FFmpeg and dependencies as described in [README.md](../README.md).
- Set `NVIDIA_API_KEY` for the current NVIDIA NIM-compatible LLM calls. The code uses `openai/gpt-oss-20b` via the NVIDIA endpoint for summaries, extraction and RAG; `MISTRAL_API_KEY` is not used by these modules.
- English uses local Whisper. Hinglish uses Sarvam and additionally needs `SARVAM_API_KEY`.
- Start with `uv run streamlit run app.py` and select **Upload Audio/Video**. The **Use Sample Recording** option depends on a file that is not checked into the repository.
- Use your own brief synthetic recording, NOT a private meeting or third-party video.

## Suggested recording script (read aloud yourself, ~20 seconds)

“Today we agreed to launch a small AI meeting assistant prototype. Asha will prepare an example dataset by Friday. Ravi will review the transcription quality on Monday. We decided to use Python and a simple Streamlit interface. The unresolved question is which embedding model gives better retrieval results.”

These are fictional names and tasks. They make it easier to check whether the application separates **decisions, action items and open questions** without implying any benchmark accuracy.

## 60-second storyboard

| Seconds | Show | Say |
| --- | --- | --- |
| 0–10 | Home screen and audio-upload input | “MeetMind converts meeting audio into structured, searchable text.” |
| 10–22 | Select English, upload the fictional recording, click Analyze | “Whisper transcribes locally; the backend splits and processes the audio.” |
| 22–36 | Intelligence tab: summary, action items, decisions, open questions | “The current app calls an LLM to extract meeting insights from the transcript.” |
| 36–48 | Transcript tab and a specific term search | “Users can inspect the underlying transcript rather than relying only on AI summaries.” |
| 48–56 | Ask MeetMind: `Who will review transcription quality?` | “Embeddings and ChromaDB retrieve relevant transcript context for an answer.” |
| 56–60 | Export tab | “The results can be exported for follow-up.” |

If a step fails, show the error honestly and fix the issue before recording a polished demo. The app currently relies on remote API access for analysis/RAG even when Whisper is local.

## Screenshot checklist (real images only)

- `docs/screenshots/01-upload.png`: input/source selection and language
- `docs/screenshots/02-intelligence.png`: successful summary, decisions and action items
- `docs/screenshots/03-rag.png`: transcript-specific question and response
- `docs/screenshots/04-transcript.png`: searchable transcript
- Optional: record one continuous 45–60 second screen capture showing the same fictional input

Never upload `.env`, real customer recordings, personal transcripts, API responses containing credentials, or the local `vector_db` directory.

## Interview questions

**Why Whisper plus an LLM?** Whisper converts audio to text; the LLM summarizes/extracts information from the transcript.

**What is RAG here?** Transcript chunks are embedded and indexed in ChromaDB; retrieval supplies context for a response. It is not model fine-tuning.

**Main limitations:** CPU transcription can be slow; cloud APIs are needed for the current summarization/RAG implementation; transcription mistakes can propagate to generated answers. There is no measured word-error rate or retrieval benchmark in this repository.
