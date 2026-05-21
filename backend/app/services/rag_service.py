"""
RAG service layer for PDF ingestion and retrieval.
"""
import uuid
from pathlib import Path

from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.ai.rag.chroma_client import get_user_vector_store
from app.ai.rag.pdf_loader import load_pdf_text
from app.ai.rag.text_splitter import get_text_splitter
from app.models.attachment import Attachment
from app.models.chat import ChatMessage, ChatThread
from app.models.user import User
from app.services.file_service import save_uploaded_files

PDF_MIME_TYPES = {"application/pdf"}


def _is_pdf_file(mime_type: str, filename: str) -> bool:
    return mime_type in PDF_MIME_TYPES or filename.lower().endswith(".pdf")


async def _resolve_or_create_thread(
    db: AsyncSession,
    user_id: uuid.UUID,
    thread_id: uuid.UUID | None,
) -> ChatThread:
    if thread_id:
        result = await db.execute(
            select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
        )
        thread = result.scalar_one_or_none()
        if thread:
            return thread

    thread = ChatThread(id=uuid.uuid4(), user_id=user_id, title=None)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def ingest_pdf_upload(
    db: AsyncSession,
    current_user: User,
    file: UploadFile,
    thread_id: uuid.UUID | None = None,
) -> tuple[ChatThread, Attachment, int]:
    """
    Save a PDF file, persist metadata, index chunks in user-scoped Chroma, and
    link the PDF attachment to a chat message in the target thread.
    """
    mime_type = (file.content_type or "").strip().lower()
    filename = Path(file.filename or "file.pdf").name
    if not _is_pdf_file(mime_type, filename):
        raise ValueError("Only PDF files are allowed")

    stored = await save_uploaded_files([file])
    if not stored or stored[0].attachment_type != "pdf":
        raise ValueError("Only PDF files are allowed")

    thread = await _resolve_or_create_thread(db, current_user.id, thread_id)

    attachment = Attachment(
        id=uuid.uuid4(),
        message_id=None,
        original_filename=stored[0].original_filename,
        stored_filename=stored[0].stored_filename,
        file_path=stored[0].file_path,
        mime_type=stored[0].mime_type,
        file_size=stored[0].file_size,
        attachment_type=stored[0].attachment_type,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    user_message = ChatMessage(
        id=uuid.uuid4(),
        thread_id=thread.id,
        role="user",
        content=f"Uploaded PDF: {attachment.original_filename}",
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    attachment.message_id = user_message.id
    await db.commit()
    await db.refresh(attachment)

    raw_text = load_pdf_text(attachment.file_path)
    if not raw_text.strip():
        return thread, attachment, 0

    splitter = get_text_splitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(raw_text)

    documents: list[Document] = []
    for idx, chunk in enumerate(chunks):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        documents.append(
            Document(
                page_content=cleaned,
                metadata={
                    "thread_id": str(thread.id),
                    "attachment_id": str(attachment.id),
                    "filename": attachment.original_filename,
                    "chunk_index": idx,
                },
            )
        )

    if not documents:
        return thread, attachment, 0

    vector_store = get_user_vector_store(current_user.id, user_email=current_user.email)
    vector_store.add_documents(documents)

    return thread, attachment, len(documents)


async def thread_has_pdf_attachments(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    stmt = (
        select(Attachment.id)
        .join(ChatMessage, Attachment.message_id == ChatMessage.id)
        .join(ChatThread, ChatMessage.thread_id == ChatThread.id)
        .where(
            ChatThread.id == thread_id,
            ChatThread.user_id == user_id,
            Attachment.attachment_type == "pdf",
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def retrieve_pdf_context(
    user_id: uuid.UUID,
    user_email: str,
    thread_id: uuid.UUID,
    question: str,
    k: int = 4,
) -> str:
    vector_store = get_user_vector_store(user_id, user_email=user_email)
    try:
        docs = vector_store.similarity_search(
            question,
            k=k,
            filter={"thread_id": str(thread_id)},
        )
    except Exception:
        return ""

    lines: list[str] = []
    for doc in docs:
        filename = str(doc.metadata.get("filename", "document"))
        content = doc.page_content.strip()
        if not content:
            continue
        lines.append(f"[{filename}]\n{content}")
    return "\n\n".join(lines)
