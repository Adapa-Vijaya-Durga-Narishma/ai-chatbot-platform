"""
File service for chat attachments.
Handles MIME/size validation and safe disk persistence.
"""
import uuid
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from starlette.datastructures import UploadFile

from app.core.config import settings


@dataclass
class StoredFileMetadata:
    original_filename: str
    stored_filename: str
    file_path: str
    mime_type: str
    file_size: int
    attachment_type: str


def _detect_attachment_type(mime_type: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if mime_type == "application/pdf" or ext == ".pdf":
        return "pdf"
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type in {"text/csv", "application/csv", "text/tab-separated-values"}:
        return "csv"
    if ext in {".csv", ".tsv"}:
        return "csv"
    if mime_type in {"application/x-tex", "text/x-tex"}:
        return "formula"
    if ext in {".tex", ".formula", ".math", ".eqn"}:
        return "formula"
    if ext in {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".cs",
        ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".sql", ".html", ".css",
        ".json", ".yaml", ".yml", ".xml", ".sh", ".ps1",
    }:
        return "code"
    if mime_type.startswith("text/"):
        return "text"
    return "other"


def _ensure_safe_upload_dir() -> Path:
    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


async def save_uploaded_files(files: list[UploadFile]) -> list[StoredFileMetadata]:
    if not files:
        raise ValueError("No files provided")

    upload_dir = _ensure_safe_upload_dir()
    saved_files: list[StoredFileMetadata] = []

    for upload in files:
        original_filename = Path(upload.filename or "file").name
        mime_type = (upload.content_type or "").strip().lower()
        if not mime_type or mime_type not in settings.allowed_mime_types:
            raise ValueError(
                f"Unsupported file format for {original_filename} ({mime_type or 'unknown'}). "
                "Allowed categories: images, videos, code, text, CSV/tables, formulas, PDFs."
            )

        content = await upload.read()
        file_size = len(content)
        if file_size == 0:
            raise ValueError(f"File is empty: {original_filename}")
        if file_size > settings.max_upload_bytes:
            raise ValueError(
                f"File exceeds max size ({settings.MAX_UPLOAD_MB} MB): {original_filename}"
            )

        suffix = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{suffix}"
        destination = (upload_dir / stored_filename).resolve()

        if upload_dir not in destination.parents:
            raise ValueError("Invalid upload path")

        async with aiofiles.open(destination, "wb") as f:
            await f.write(content)

        saved_files.append(
            StoredFileMetadata(
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_path=f"{settings.UPLOAD_DIR.rstrip('/')}/{stored_filename}",
                mime_type=mime_type,
                file_size=file_size,
                attachment_type=_detect_attachment_type(mime_type, original_filename),
            )
        )

    return saved_files
