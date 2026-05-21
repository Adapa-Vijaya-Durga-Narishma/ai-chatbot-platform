"""
ChromaDB client helpers for per-user collections.
"""
import uuid

from langchain_community.vectorstores import Chroma

from app.ai.rag.embeddings import build_embeddings
from app.core.config import settings


def get_user_collection_name(user_id: uuid.UUID) -> str:
    return f"user_{user_id}"


def get_user_vector_store(user_id: uuid.UUID, user_email: str | None = None) -> Chroma:
    return Chroma(
        collection_name=get_user_collection_name(user_id),
        embedding_function=build_embeddings(user_email=user_email),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )
