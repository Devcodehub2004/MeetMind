import os
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
    model="openai/gpt-oss-20b",
    api_key=os.getenv("NVIDIA_API_KEY"),
    base_url="https://integrate.api.nvidia.com/v1",
    temperature=0.3
)


def split_transcript(transcript: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
    )
    return splitter.split_text(transcript)


# --- title ------------------------------------------------------------------

_TITLE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Based on the meeting transcript, generate a short professional meeting title "
        "(max 8 words). Only return the title, nothing else.",
    ),
    ("human", "{text}"),
])

_title_chain = _TITLE_PROMPT | get_llm() | StrOutputParser()


def generate_title(transcript: str) -> str:
    return _title_chain.invoke({"text": transcript[:2000]}).strip()


# --- summary ----------------------------------------------------------------

_MAP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Summarize this portion of a meeting transcript concisely."),
    ("human", "{text}"),
])

_COMBINE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert meeting summarizer. Combine these partial summaries "
        "into one final professional meeting summary in bullet points.",
    ),
    ("human", "{text}"),
])

_map_chain = _MAP_PROMPT | get_llm() | StrOutputParser()
_combine_chain = _COMBINE_PROMPT | get_llm() | StrOutputParser()


def summarize(transcript: str) -> str:
    chunks = split_transcript(transcript)

    # Short transcript -> single call, no map-reduce needed
    if len(chunks) <= 1:
        return _combine_chain.invoke({"text": transcript})

    chunk_summaries = [_map_chain.invoke({"text": c}) for c in chunks]
    combined = "\n\n".join(chunk_summaries)
    return _combine_chain.invoke({"text": combined})