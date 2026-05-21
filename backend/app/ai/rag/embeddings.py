"""
Embedding client factory for RAG.
"""
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def build_embeddings(user_email: str | None = None) -> OpenAIEmbeddings:
    model_kwargs = {"user": user_email} if user_email else {}
    return OpenAIEmbeddings(
        model=settings.LITELLM_EMBEDDING_MODEL,
        base_url=settings.LITELLM_PROXY_URL,
        api_key=settings.LITELLM_API_KEY,
        model_kwargs=model_kwargs,
    )
