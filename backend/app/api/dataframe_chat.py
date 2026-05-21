"""HTTP layer for dataframe-backed querying."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.dataframe import (
    DataframeQueryRequest,
    DataframeQueryResponse,
    DataframeSourceResponse,
    GoogleSheetConnectRequest,
)
from app.services.dataframe_chat_service import (
    DataframeAgentError,
    DataframeSessionError,
    ask_dataframe_question,
    store_google_sheet_dataframe,
    store_uploaded_dataframe,
)
from app.services.dataframe_service import DataframeLoadError
from app.services.sheets_service import SheetLoadError

router = APIRouter()


@router.post("/upload", response_model=DataframeSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataframe(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> DataframeSourceResponse:
    try:
        result = await store_uploaded_dataframe(current_user, file)
    except DataframeLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_upload", "message": str(exc)},
        )

    return DataframeSourceResponse(**result)


@router.post("/google-sheet", response_model=DataframeSourceResponse)
async def connect_google_sheet(
    request: GoogleSheetConnectRequest,
    current_user: User = Depends(get_current_user),
) -> DataframeSourceResponse:
    try:
        result = store_google_sheet_dataframe(current_user, request.sheet_url)
    except (SheetLoadError, DataframeLoadError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_sheet", "message": str(exc)},
        )

    return DataframeSourceResponse(**result)


@router.post("/query", response_model=DataframeQueryResponse)
async def query_dataframe(
    request: DataframeQueryRequest,
    current_user: User = Depends(get_current_user),
) -> DataframeQueryResponse:
    try:
        result = await ask_dataframe_question(current_user, request.question)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(exc)},
        )
    except DataframeSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "dataframe_not_loaded", "message": str(exc)},
        )
    except DataframeAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "agent_failure", "message": str(exc)},
        )

    return DataframeQueryResponse(**result)