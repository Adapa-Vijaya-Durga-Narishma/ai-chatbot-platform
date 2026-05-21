import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.attachment import AttachmentUploadResponse
from app.schemas.rag import PdfUploadResponse
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ImageGenerationChatResponse,
    ChatThreadCreate,
    ChatThreadResponse,
    ChatThreadUpdate,
)
from app.services.chat_service import (
    create_thread,
    delete_thread,
    get_messages,
    get_threads,
    handle_image_generation_chat_request,
    rename_thread,
    stream_chat_response,
    upload_attachments,
)
from app.services.rag_service import ingest_pdf_upload
from app.services.image_generation_service import is_image_generation_prompt
from openai import OpenAIError

router = APIRouter()


@router.post("", response_model=None)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Check mode from request, fall back to prompt detection for backward compatibility
    is_image_mode = request.mode == "generate-image" or is_image_generation_prompt(request.message)
    
    if is_image_mode:
        try:
            thread, assistant_message = await handle_image_generation_chat_request(
                db=db,
                message=request.message,
                current_user=current_user,
                thread_id=request.thread_id,
                attachment_ids=request.attachment_ids,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_prompt", "message": str(exc)},
            )
        except OpenAIError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"error": "llm_error", "message": str(exc)},
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "unexpected", "message": str(exc)},
            )

        return ImageGenerationChatResponse(
            thread_id=thread.id,
            message=ChatMessageResponse.model_validate(assistant_message),
        )

    # Determine if RAG should be used based on mode
    use_rag = request.mode == "upload-pdf"

    async def generate():
        async for token in stream_chat_response(
            db=db,
            message=request.message,
            current_user=current_user,
            thread_id=request.thread_id,
            attachment_ids=request.attachment_ids,
            use_rag=use_rag,
        ):
            yield token

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/upload", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_chat_files(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttachmentUploadResponse:
    try:
        attachments = await upload_attachments(db, current_user.id, files)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_upload", "message": str(exc)},
        )
    return AttachmentUploadResponse(attachments=attachments)


@router.post("/upload-pdf", response_model=PdfUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    thread_id: uuid.UUID | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PdfUploadResponse:
    try:
        thread, attachment, chunks_indexed = await ingest_pdf_upload(
            db=db,
            current_user=current_user,
            file=file,
            thread_id=thread_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_upload", "message": str(exc)},
        )

    status_text = "ready" if chunks_indexed > 0 else "uploaded_no_text"
    return PdfUploadResponse(
        thread_id=thread.id,
        attachment=attachment,
        chunks_indexed=chunks_indexed,
        status=status_text,
    )


@router.get("/threads", response_model=list[ChatThreadResponse])
async def list_threads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatThreadResponse]:
    threads = await get_threads(db, current_user.id)
    return [ChatThreadResponse.model_validate(t) for t in threads]


@router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread_route(
    payload: ChatThreadCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatThreadResponse:
    thread = await create_thread(db, current_user.id, payload.title)
    return ChatThreadResponse.model_validate(thread)


@router.patch("/threads/{thread_id}", response_model=ChatThreadResponse)
async def rename_thread_route(
    thread_id: uuid.UUID,
    payload: ChatThreadUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatThreadResponse:
    thread = await rename_thread(db, thread_id, current_user.id, payload.title)
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Thread not found"},
        )
    return ChatThreadResponse.model_validate(thread)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread_route(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await delete_thread(db, thread_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Thread not found"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageResponse]:
    messages = await get_messages(db, thread_id, current_user.id)
    return [ChatMessageResponse.model_validate(m) for m in messages]