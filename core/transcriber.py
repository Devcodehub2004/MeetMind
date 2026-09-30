import os
import requests
import whisper

from pydub import AudioSegment
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Sarvam sync API accepts audio up to 30 seconds.
# We use 25 seconds to leave a safety margin.
SARVAM_PIECE_SECONDS = 25

# Whisper model used for English audio
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# Sarvam API configuration
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

SARVAM_STT_TRANSLATE_URL = (
    "https://api.sarvam.ai/speech-to-text-translate"
)

SARVAM_MODEL = os.getenv(
    "SARVAM_STT_MODEL",
    "saaras:v2.5"
)


# Whisper model cache
_model = None


# ─────────────────────────────────────────────────────────────────────────────
# Whisper
# ─────────────────────────────────────────────────────────────────────────────

def load_model():
    """
    Load Whisper model only once.

    Loading the model every time would be very slow,
    so we keep it in the global variable _model.
    """

    global _model

    if _model is None:

        print(f"Loading Whisper model: {WHISPER_MODEL} ...")

        _model = whisper.load_model(WHISPER_MODEL)

        print("Whisper model loaded.")

    return _model


def transcribe_chunk_whisper(chunk_path: str) -> str:
    """
    Transcribe one audio chunk using local Whisper.
    """

    print(f"Whisper processing: {chunk_path}")

    model = load_model()

    result = model.transcribe(
        chunk_path,
        task="transcribe"
    )

    text = result.get("text", "").strip()

    print("Whisper transcription completed.")

    return text


# ─────────────────────────────────────────────────────────────────────────────
# Sarvam API
# ─────────────────────────────────────────────────────────────────────────────

def _send_to_sarvam(piece_path: str) -> str:
    """
    Send one <=25 second WAV file to Sarvam
    and return the English transcript.
    """

    if not SARVAM_API_KEY:
        raise RuntimeError(
            "SARVAM_API_KEY is not set. "
            "Check your .env file."
        )

    print("Opening audio file...")

    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }

    with open(piece_path, "rb") as f:

        files = {
            "file": (
                os.path.basename(piece_path),
                f,
                "audio/wav"
            )
        }

        data = {
            "model": SARVAM_MODEL,
            "with_diarization": "false"
        }

        print("BEFORE SARVAM REQUEST")

        try:

            response = requests.post(
                SARVAM_STT_TRANSLATE_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )

        except requests.exceptions.Timeout:

            print("❌ Sarvam request timed out after 120 seconds.")

            raise RuntimeError(
                "Sarvam API request timed out after 120 seconds."
            )

        except requests.exceptions.ConnectionError as e:

            print("❌ Could not connect to Sarvam API.")
            print(e)

            raise RuntimeError(
                "Could not connect to Sarvam API. "
                "Check your internet connection."
            )

        except requests.exceptions.RequestException as e:

            print("❌ Sarvam request failed.")
            print(e)

            raise RuntimeError(
                f"Sarvam API request failed: {e}"
            )

    print("AFTER SARVAM REQUEST")

    print("Sarvam status code:", response.status_code)

    print(
        "Sarvam response:",
        response.text[:500]
    )

    # Handle errors
    if not response.ok:

        print(
            f"❌ Sarvam returned HTTP {response.status_code}"
        )

        response.raise_for_status()

    # Convert response to JSON
    try:

        result = response.json()

    except ValueError:

        raise RuntimeError(
            "Sarvam returned an invalid JSON response."
        )

    # Get transcript
    transcript = result.get("transcript", "")

    if not transcript:

        print("⚠️ Sarvam returned an empty transcript.")

    return transcript.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Sarvam transcription
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_chunk_sarvam(chunk_path: str) -> str:
    """
    Split an audio chunk into <=25 second pieces,
    send each piece to Sarvam,
    and combine the results.
    """

    if not SARVAM_API_KEY:

        raise RuntimeError(
            "SARVAM_API_KEY is not set in environment / .env"
        )

    print(f"Loading WAV: {chunk_path}")

    # Load WAV
    try:

        audio = AudioSegment.from_wav(chunk_path)

    except Exception as e:

        print("❌ Could not load WAV file.")
        print(e)

        raise RuntimeError(
            f"Could not load WAV file: {e}"
        )

    duration_seconds = len(audio) / 1000

    print(
        f"Audio loaded successfully: "
        f"{duration_seconds:.2f} seconds"
    )

    piece_ms = SARVAM_PIECE_SECONDS * 1000

    full_text = ""

    total_pieces = (
        len(audio) + piece_ms - 1
    ) // piece_ms

    print(
        f"Total Sarvam pieces: {total_pieces}"
    )

    # Split audio
    for i, start in enumerate(
        range(0, len(audio), piece_ms)
    ):

        piece_number = i + 1

        print(
            f"\nPreparing Sarvam piece "
            f"{piece_number}/{total_pieces}..."
        )

        piece = audio[
            start:start + piece_ms
        ]

        piece_path = (
            f"{chunk_path}_sv_{i}.wav"
        )

        try:

            # Export temporary WAV
            print(
                f"Exporting piece "
                f"{piece_number}/{total_pieces}..."
            )

            piece.export(
                piece_path,
                format="wav"
            )

            print(
                f"→ Sending piece "
                f"{piece_number}/{total_pieces} "
                f"to Sarvam..."
            )

            # Send to Sarvam
            text = _send_to_sarvam(
                piece_path
            )

            print(
                f"← Sarvam response received "
                f"for piece {piece_number}"
            )

            if text:

                full_text += text + " "

        finally:

            # Delete temporary piece
            if os.path.exists(piece_path):

                os.remove(piece_path)

                print(
                    f"Deleted temporary piece: "
                    f"{piece_path}"
                )

    print("\n✅ All Sarvam pieces completed.")

    return full_text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Transcription router
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_chunk(
    chunk_path: str,
    language: str = "english"
) -> str:
    """
    Choose transcription engine.

    english  → local Whisper
    hinglish → Sarvam AI
    """

    language = language.lower().strip()

    if language == "hinglish":

        print(
            "Using Sarvam AI for this chunk."
        )

        return transcribe_chunk_sarvam(
            chunk_path
        )

    else:

        print(
            "Using local Whisper for this chunk."
        )

        return transcribe_chunk_whisper(
            chunk_path
        )


# ─────────────────────────────────────────────────────────────────────────────
# Transcribe all chunks
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_all(
    chunks: list,
    language: str = "english"
) -> str:
    """
    Transcribe all audio chunks and combine
    them into one transcript.
    """

    if not chunks:

        raise ValueError(
            "No audio chunks were provided."
        )

    full_transcript = ""

    if language.lower() == "hinglish":

        engine = "Sarvam AI"

    else:

        engine = "Whisper"

    print(
        f"\nUsing {engine} for transcription."
    )

    print(
        f"Total chunks: {len(chunks)}"
    )

    for i, chunk in enumerate(chunks):

        print(
            f"\n{'=' * 60}"
        )

        print(
            f"Transcribing chunk "
            f"{i + 1}/{len(chunks)}..."
        )

        print(
            f"File: {chunk}"
        )

        try:

            text = transcribe_chunk(
                chunk,
                language=language
            )

            if text:

                full_transcript += (
                    text + " "
                )

                print(
                    f"Chunk {i + 1} completed."
                )

            else:

                print(
                    f"⚠️ Chunk {i + 1} "
                    f"returned empty text."
                )

        except Exception as e:

            print(
                f"\n❌ Error while "
                f"transcribing chunk "
                f"{i + 1}:"
            )

            print(e)

            raise

    print(
        f"\n{'=' * 60}"
    )

    print(
        "✅ Transcription complete."
    )

    return full_transcript.strip()