"""
LiteLLM client singletons.

All AI calls in this project MUST import from this module.
Never instantiate ChatOpenAI, OpenAI, or OpenAIEmbeddings anywhere else.

Usage tracking note: every call must pass the authenticated user's email
via `user=` (OpenAI SDK) or config={"metadata": {"user_email": ...}} (LangChain).
"""
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI

from app.core.config import settings

# ── LangChain LLM (for LCEL chains) ──────────────────────────────────────────
llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    base_url=settings.LITELLM_PROXY_URL,
    api_key=settings.LITELLM_API_KEY,
    timeout=30,
    max_retries=2,
)

# ── OpenAI SDK client (for direct calls: image gen, embeddings) ───────────────
openai_client = OpenAI(
    api_key=settings.LITELLM_API_KEY,
    base_url=settings.LITELLM_PROXY_URL,
)

# ── Embeddings (for RAG / ChromaDB ingestion) ─────────────────────────────────
embeddings = OpenAIEmbeddings(
    model=settings.LITELLM_EMBEDDING_MODEL,
    base_url=settings.LITELLM_PROXY_URL,
    api_key=settings.LITELLM_API_KEY,
)
