"""
Chat service layer — all business logic here, no FastAPI imports.
Handles thread management, message persistence, and LLM streaming.
"""
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
import base64
import io
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.datastructures import UploadFile
from openai import OpenAIError
import cv2

from app.ai.chains.chat_chain import chat_chain
from app.ai.chains.rag_chain import rag_chain
from app.ai.chains.thread_title_chain import generate_thread_title
from app.ai.llm import openai_client
from app.ai.memory.conversation_memory import get_recent_messages
from app.core.config import settings
from app.models.attachment import Attachment
from app.models.chat import ChatMessage, ChatThread
from app.models.user import User
from app.services.file_service import save_uploaded_files
from app.services.image_generation_service import (
    create_generated_image_message,
    extract_image_prompt,
)
from app.services.rag_service import retrieve_pdf_context, thread_has_pdf_attachments


# ── Thread management ─────────────────────────────────────────────────────────

async def create_thread(db: AsyncSession, user_id: uuid.UUID, title: str | None = None) -> ChatThread:
    thread = ChatThread(id=uuid.uuid4(), user_id=user_id, title=title)
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return thread


async def get_threads(db: AsyncSession, user_id: uuid.UUID) -> list[ChatThread]:
    result = await db.execute(
        select(ChatThread)
        .where(ChatThread.user_id == user_id)
        .order_by(ChatThread.created_at.desc())
    )
    return list(result.scalars().all())


async def rename_thread(
    db: AsyncSession,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> ChatThread | None:
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        return None
    thread.title = title
    await db.commit()
    await db.refresh(thread)
    return thread


async def delete_thread(db: AsyncSession, thread_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        return False
    await db.delete(thread)
    await db.commit()
    return True


async def get_messages(db: AsyncSession, thread_id: uuid.UUID, user_id: uuid.UUID) -> list[ChatMessage]:
    """Return messages for a thread, validating ownership first."""
    result = await db.execute(
        select(ChatThread)
        .where(ChatThread.id == thread_id, ChatThread.user_id == user_id)
        .options(selectinload(ChatThread.messages).selectinload(ChatMessage.attachments))
    )
    thread = result.scalar_one_or_none()
    if not thread:
        return []
    return thread.messages


# ── Message persistence ───────────────────────────────────────────────────────

async def save_message(
    db: AsyncSession, thread_id: uuid.UUID, role: str, content: str
) -> ChatMessage:
    msg = ChatMessage(id=uuid.uuid4(), thread_id=thread_id, role=role, content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def upload_attachments(
    db: AsyncSession,
    user_id: uuid.UUID,
    files: list[UploadFile],
) -> list[Attachment]:
    _ = user_id
    stored_files = await save_uploaded_files(files)
    attachments: list[Attachment] = []

    for stored in stored_files:
        attachment = Attachment(
            id=uuid.uuid4(),
            message_id=None,
            original_filename=stored.original_filename,
            stored_filename=stored.stored_filename,
            file_path=stored.file_path,
            mime_type=stored.mime_type,
            file_size=stored.file_size,
            attachment_type=stored.attachment_type,
        )
        db.add(attachment)
        attachments.append(attachment)

    await db.commit()
    for attachment in attachments:
        await db.refresh(attachment)
    return attachments


async def link_attachments_to_message(
    db: AsyncSession,
    message_id: uuid.UUID,
    attachment_ids: list[uuid.UUID] | None,
) -> list[Attachment]:
    if not attachment_ids:
        return []

    result = await db.execute(
        select(Attachment).where(
            Attachment.id.in_(attachment_ids),
            Attachment.message_id.is_(None),
        )
    )
    attachments = list(result.scalars().all())
    if len(attachments) != len(set(attachment_ids)):
        raise ValueError("One or more attachments are invalid or already linked")

    for attachment in attachments:
        attachment.message_id = message_id
    await db.commit()
    return attachments


async def _extract_video_frame_insights(attachments: list[Attachment], user_email: str) -> str:
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    video_types = {"video"}
    insights: list[str] = []
    processed_count = 0
    max_videos = 3

    for attachment in attachments:
        if attachment.attachment_type not in video_types:
            continue
        if processed_count >= max_videos:
            break

        candidate = Path(attachment.file_path).resolve()
        if upload_dir not in candidate.parents:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue

        try:
            cap = cv2.VideoCapture(str(candidate))
            if not cap.isOpened():
                continue

            frame_count = 0
            max_frames_to_skip = 5
            frame_extracted = False

            while frame_count < max_frames_to_skip:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                if frame is None or frame.size == 0:
                    continue
                if cv2.countNonZero(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)) < frame.size * 0.05:
                    continue

                _, buffer = cv2.imencode(".jpg", frame)
                b64_frame = base64.b64encode(buffer).decode("utf-8")
                frame_extracted = True
                break

            cap.release()

            if not frame_extracted:
                insights.append(f"[Video: {attachment.original_filename}] No analyzable frames found.")
                processed_count += 1
                continue

            try:
                response = openai_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_frame}",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": "This is a frame extracted from a video. Describe what you see in detail. Include any text, UI elements, dialogs, or code visible on screen.",
                                },
                            ],
                        }
                    ],
                    user=user_email,
                    max_tokens=500,
                )
                description = response.choices[0].message.content.strip()
                insights.append(f"[Video frame: {attachment.original_filename}]\n{description}")
                processed_count += 1
            except OpenAIError:
                continue
        except Exception:
            continue

    return "\n\n".join(insights)


async def _extract_image_insights(attachments: list[Attachment], user_email: str) -> str:
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    image_types = {"image"}
    insights: list[str] = []
    processed_count = 0
    max_images = 5

    for attachment in attachments:
        if attachment.attachment_type not in image_types:
            continue
        if processed_count >= max_images:
            break

        candidate = Path(attachment.file_path).resolve()
        if upload_dir not in candidate.parents:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue

        try:
            image_data = candidate.read_bytes()
            b64_image = base64.b64encode(image_data).decode("utf-8")
        except OSError:
            continue

        try:
            response = openai_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{attachment.mime_type};base64,{b64_image}",
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract and read all text, data, and content from this image. If it's a table, spreadsheet, or data grid, transcribe the rows and columns exactly. If it's a document or screenshot, extract all visible text. If it's a diagram or chart, describe the structure and any labels. Be thorough and precise.",
                            },
                        ],
                    }
                ],
                user=user_email,
                max_tokens=1000,
            )
            description = response.choices[0].message.content.strip()
            insights.append(f"[Image: {attachment.original_filename}]\n{description}")
            processed_count += 1
        except OpenAIError:
            continue

    return "\n\n".join(insights)


def _extract_text_attachment_context(attachments: list[Attachment]) -> str:
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    supported_types = {"text", "code", "csv", "formula"}
    snippets: list[str] = []
    total_budget = 12_000

    for attachment in attachments:
        if attachment.attachment_type not in supported_types:
            continue
        if total_budget <= 0:
            break

        candidate = Path(attachment.file_path).resolve()
        if upload_dir not in candidate.parents:
            continue
        if not candidate.exists() or not candidate.is_file():
            continue

        try:
            raw_bytes = candidate.read_bytes()
            decoded = raw_bytes.decode("utf-8", errors="replace")
        except OSError:
            continue

        per_file_limit = min(3000, total_budget)
        snippet = decoded[:per_file_limit].strip()
        if not snippet:
            continue

        snippets.append(f"[{attachment.original_filename}]\n{snippet}")
        total_budget -= len(snippet)

    return "\n\n".join(snippets)


async def _format_attachment_context(attachments: list[Attachment], user_email: str) -> str:
    if not attachments:
        return "None"

    lines = ["User attached the following files:"]
    for attachment in attachments:
        size_kb = max(1, round(attachment.file_size / 1024))
        lines.append(
            f"- {attachment.original_filename} ({attachment.attachment_type}, {attachment.mime_type}, {size_kb} KB)"
        )

    text_context = _extract_text_attachment_context(attachments)
    if text_context:
        lines.append("")
        lines.append("Extracted text snippets from supported attachments:")
        lines.append(text_context)

    image_insights = await _extract_image_insights(attachments, user_email)
    if image_insights:
        lines.append("")
        lines.append("Image analysis results:")
        lines.append(image_insights)

    video_insights = await _extract_video_frame_insights(attachments, user_email)
    if video_insights:
        lines.append("")
        lines.append("Video frame analysis results:")
        lines.append(video_insights)

    lines.append("Use the above context to answer questions about the attachments.")
    return "\n".join(lines)


def _extract_rag_source_filenames(rag_context: str) -> list[str]:
    if not rag_context.strip():
        return []

    filenames = re.findall(r"^\[([^\]]+)\]", rag_context, flags=re.MULTILINE)
    unique_filenames: list[str] = []
    for name in filenames:
        cleaned = name.strip()
        if cleaned and cleaned not in unique_filenames:
            unique_filenames.append(cleaned)
    return unique_filenames


async def _should_generate_title(
    db: AsyncSession,
    thread: ChatThread,
    created_new_thread: bool,
) -> bool:
    """Decide whether the current user turn should generate a thread title."""
    if created_new_thread:
        return True
    if thread.title:
        return False

    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.thread_id == thread.id)
    )
    message_count = count_result.scalar_one()
    if message_count == 1:
        return True

    # Upload-first PDF flow stores a marker message as the first turn.
    # When the first real question arrives, count becomes 2 and we should title then.
    if message_count == 2:
        first_message_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        first_message = first_message_result.scalar_one_or_none()
        if (
            first_message
            and first_message.role == "user"
            and first_message.content.startswith("Uploaded PDF:")
        ):
            return True

    return False


# ── LLM streaming + persistence ───────────────────────────────────────────────

async def stream_chat_response(
    db: AsyncSession,
    message: str,
    current_user: User,
    thread_id: uuid.UUID | None = None,
    attachment_ids: list[uuid.UUID] | None = None,
    use_rag: bool = False,
) -> AsyncGenerator[str, None]:
    """
    1. Get or create thread
    2. Save user message
    3. Stream LLM response token-by-token
    4. Save completed assistant response
    Yields tokens plus a final JSON line: data: {"thread_id": "..."}
    """
    # Resolve or create thread
    created_new_thread = False
    if thread_id:
        result = await db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == current_user.id,
            )
        )
        thread = result.scalar_one_or_none()
        if not thread:
            thread = await create_thread(db, current_user.id)
            created_new_thread = True
    else:
        thread = await create_thread(db, current_user.id, title=None)
        created_new_thread = True

    # Save user message before building memory context.
    # We exclude this new message from history to avoid duplication in the prompt.
    user_msg = await save_message(db, thread.id, "user", message)
    linked_attachments = await link_attachments_to_message(db, user_msg.id, attachment_ids)
    attachment_context = await _format_attachment_context(linked_attachments, current_user.email)

    history = await get_recent_messages(
        db=db,
        thread_id=thread.id,
        user_id=current_user.id,
        limit=5,
        exclude_message_id=user_msg.id,
    )

    # In normal chat mode, do not let document-thread history bleed into replies.
    # This keeps normal mode independent from previous RAG answers.
    if not use_rag and await thread_has_pdf_attachments(db, thread.id, current_user.id):
        history = []

    if await _should_generate_title(db, thread, created_new_thread):
        try:
            generated_title = await generate_thread_title(message, current_user.email)
        except Exception:
            generated_title = " ".join(message.strip().split())[:50]
        if generated_title:
            thread = await rename_thread(db, thread.id, current_user.id, generated_title)
            if thread is None:
                # Ownership changed unexpectedly; stop safely.
                return

    # Only use RAG if explicitly requested via use_rag parameter
    rag_context = ""
    if use_rag:
        rag_context = retrieve_pdf_context(
            user_id=current_user.id,
            user_email=current_user.email,
            thread_id=thread.id,
            question=message,
            k=4,
        )

    # Stream LLM response
    should_use_rag_chain = use_rag and bool(rag_context.strip())
    full_response: list[str] = []
    if should_use_rag_chain:
        response_stream = rag_chain.stream(
            {
                "history": history,
                "human_input": message,
                "context": rag_context,
            },
            config={"metadata": {"user_email": current_user.email}},
        )
    else:
        response_stream = chat_chain.stream(
            {
                "history": history,
                "human_input": message,
                "attachment_context": attachment_context,
            },
            config={"metadata": {"user_email": current_user.email}},
        )

    for chunk in response_stream:
        token = chunk.content if hasattr(chunk, "content") else str(chunk)
        if token:
            full_response.append(token)
            yield token

    if should_use_rag_chain:
        current_response_text = "".join(full_response)
        citation_files = _extract_rag_source_filenames(rag_context)
        already_has_citations = "sources:" in current_response_text.lower()
        if citation_files and not already_has_citations:
            citations_text = "\n\nSources: " + ", ".join(citation_files)
            full_response.append(citations_text)
            yield citations_text

    # Persist completed assistant response
    assistant_content = "".join(full_response)
    if assistant_content:
        await save_message(db, thread.id, "assistant", assistant_content)

    # Yield thread_id so frontend can correlate the response
    yield f'\n\ndata: {{"thread_id": "{thread.id}"}}'


async def handle_image_generation_chat_request(
    db: AsyncSession,
    message: str,
    current_user: User,
    thread_id: uuid.UUID | None = None,
    attachment_ids: list[uuid.UUID] | None = None,
) -> tuple[ChatThread, ChatMessage]:
    """
    Process an image-generation chat turn and return the persisted assistant message.
    """
    created_new_thread = False
    if thread_id:
        result = await db.execute(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == current_user.id,
            )
        )
        thread = result.scalar_one_or_none()
        if not thread:
            thread = await create_thread(db, current_user.id)
            created_new_thread = True
    else:
        thread = await create_thread(db, current_user.id, title=None)
        created_new_thread = True

    user_msg = await save_message(db, thread.id, "user", message)
    await link_attachments_to_message(db, user_msg.id, attachment_ids)

    if await _should_generate_title(db, thread, created_new_thread):
        try:
            generated_title = await generate_thread_title(message, current_user.email)
        except Exception:
            generated_title = " ".join(message.strip().split())[:50]
        if generated_title:
            thread = await rename_thread(db, thread.id, current_user.id, generated_title)
            if thread is None:
                raise ValueError("Thread ownership changed unexpectedly")

    image_prompt = extract_image_prompt(message)
    assistant_message = await create_generated_image_message(
        db=db,
        thread_id=thread.id,
        user_email=current_user.email,
        prompt=image_prompt,
    )
    return thread, assistant_message
