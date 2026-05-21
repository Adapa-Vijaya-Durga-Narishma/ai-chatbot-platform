"""
PDF loader utilities for RAG ingestion.
"""
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader


def load_pdf_text(pdf_path: str) -> str:
    """Load a PDF from disk and return normalized text content."""
    path = Path(pdf_path).resolve()
    loader = PyPDFLoader(str(path))
    documents = loader.load()
    pages = [doc.page_content.strip() for doc in documents if doc.page_content and doc.page_content.strip()]
    return "\n\n".join(pages)
