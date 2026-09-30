import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
    )


def _split(transcript: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    return splitter.split_text(transcript)


def build_vector_store(transcript: str, source: str = "unknown") -> Chroma:
    """
    Build a *fresh* vector store for one transcript.
    Any previous collection with the same name is dropped first so
    multiple runs don't contaminate each other.
    """
    print("Building vector store")

    chunks = _split(transcript)
    docs = [
        Document(
            page_content=chunk,
            metadata={"chunk_index": i, "source": source},
        )
        for i, chunk in enumerate(chunks)
    ]

    embeddings = get_embeddings()

    # Drop any prior collection so this run starts clean
    try:
        old = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
        old.delete_collection()
    except Exception:
        # Nothing to delete on first run
        pass

    vector_store = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DIR,
    )
    return vector_store


def load_vector_store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )


def get_retriever(vector_store: Chroma, k: int = 4):
    return vector_store.as_retriever(
        search_type="mmr",                 # better diversity than plain similarity
        search_kwargs={"k": k, "fetch_k": k * 4},
    )