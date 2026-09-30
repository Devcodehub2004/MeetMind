# core/extractor.py
# Actionable items, decisions, questions

import os
import json
import re
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda


# --- shared LLM --------------------------------------------------------------

@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.3
)
        
       
    


def build_chain(system_prompt: str):
    """Legacy helper: text -> text chain with a custom system prompt."""
    return (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{text}"),
        ])
        | get_llm()
        | StrOutputParser()
    )


# --- prompts for the individual (legacy) extractors --------------------------

_ACTION_PROMPT = (
    "You are an expert meeting analyst. From the meeting transcript, "
    "extract all action items. For each provide:\n"
    "- Task description\n"
    "- Owner (who is responsible)\n"
    "- Deadline (if mentioned, else write 'Not specified')\n\n"
    "Format as a numbered list. If none found say 'No action items found.'"
)

_DECISION_PROMPT = (
    "You are an expert meeting analyst. From the meeting transcript, "
    "extract all key decisions made. Format as a numbered list. "
    "If none found say 'No key decisions found.'"
)

_QUESTION_PROMPT = (
    "From the meeting transcript, extract all unresolved questions "
    "or topics needing follow-up. Format as a numbered list. "
    "If none found say 'No open questions found.'"
)


def extract_action_items(transcript: str) -> str:
    return build_chain(_ACTION_PROMPT).invoke(transcript)


def extract_key_decisions(transcript: str) -> str:
    return build_chain(_DECISION_PROMPT).invoke(transcript)


def extract_questions(transcript: str) -> str:
    return build_chain(_QUESTION_PROMPT).invoke(transcript)


# --- single-call extractor (preferred) ---------------------------------------

_EXTRACT_ALL_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert meeting analyst. Read the transcript and return a "
        "single JSON object with EXACTLY these keys:\n"
        '  "title": short professional meeting title, max 8 words\n'
        '  "summary": bullet-point meeting summary\n'
        '  "action_items": numbered list; each item has task, owner, deadline '
        '(use "Not specified" when unknown)\n'
        '  "key_decisions": numbered list of decisions made\n'
        '  "open_questions": numbered list of unresolved questions / follow-ups\n\n'
        "Rules:\n"
        "- Output ONLY valid JSON. No markdown fences, no commentary.\n"
        "- If a section has no content, use the string \"None\".\n"
        "- Keep each list concise; do not invent information not in the transcript.",
    ),
    ("human", "{text}"),
])

_extract_all_chain = _EXTRACT_ALL_PROMPT | get_llm() | StrOutputParser()

_DEFAULT_KEYS = ("title", "summary", "action_items", "key_decisions", "open_questions")


def _strip_code_fences(raw: str) -> str:
    """Remove ```json ... ``` fences Mistral sometimes adds."""
    raw = raw.strip()
    if raw.startswith("```"):
        # drop opening fence (optionally with language tag)
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        # drop trailing fence
        raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _fallback_payload(transcript: str, raw: str) -> dict:
    first_sentence = transcript.strip().split(".")[0][:60] or "Untitled"
    return {
        "title": first_sentence,
        "summary": raw or "None",
        "action_items": "None",
        "key_decisions": "None",
        "open_questions": "None",
    }


def extract_all(transcript: str) -> dict:
    """
    One LLM call that returns title + summary + action items + decisions + questions.
    Falls back gracefully if the model returns malformed JSON.
    """
    raw = _extract_all_chain.invoke({"text": transcript[:12000]}).strip()
    cleaned = _strip_code_fences(raw)

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("expected JSON object")
    except (json.JSONDecodeError, ValueError):
        return _fallback_payload(transcript, raw)

    # Ensure every key is present and non-empty
    for key in _DEFAULT_KEYS:
        value = data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            data[key] = "None"

    return {k: data[k] for k in _DEFAULT_KEYS}