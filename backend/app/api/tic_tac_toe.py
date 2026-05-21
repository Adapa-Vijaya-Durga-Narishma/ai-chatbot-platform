"""
Tic Tac Toe API router — HTTP only, no business logic.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tic_tac_toe import (
    GameCreateRequest,
    GameResponse,
    MoveResponse,
    PlayerMoveRequest,
)
from app.services.tic_tac_toe_service import (
    GameAlreadyCompletedError,
    GameNotFoundError,
    InvalidMoveError,
    NotPlayerTurnError,
    UnauthorizedGameAccessError,
    build_game_response,
    create_new_game,
    get_game,
    get_user_games,
    make_player_move,
    restart_game,
)

router = APIRouter()


@router.post("/new-game", response_model=GameResponse)
async def create_game(
    request: GameCreateRequest = GameCreateRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameResponse:
    """Create a new Tic Tac Toe game with specified difficulty."""
    game = await create_new_game(db, current_user.id, request.difficulty)
    return GameResponse(**build_game_response(game))


@router.post("/move", response_model=MoveResponse)
async def player_move(
    request: PlayerMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MoveResponse:
    """Make a player move and receive AI response."""
    try:
        game, player_move_result, ai_move, message, ai_reasoning = await make_player_move(
            db=db,
            game_id=request.game_id,
            user_id=current_user.id,
            row=request.row,
            col=request.col,
            user_email=current_user.email,
        )
        return MoveResponse(
            game=GameResponse(**build_game_response(game, ai_reasoning)),
            player_move=player_move_result,
            ai_move=ai_move,
            ai_reasoning=ai_reasoning,
            message=message,
        )
    except GameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)},
        )
    except UnauthorizedGameAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": str(e)},
        )
    except GameAlreadyCompletedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "game_completed", "message": str(e)},
        )
    except NotPlayerTurnError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "not_your_turn", "message": str(e)},
        )
    except InvalidMoveError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_move", "message": str(e)},
        )


@router.get("/{game_id}", response_model=GameResponse)
async def get_game_by_id(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameResponse:
    """Get a specific game by ID."""
    try:
        game = await get_game(db, game_id, current_user.id)
        return GameResponse(**build_game_response(game))
    except GameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)},
        )
    except UnauthorizedGameAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": str(e)},
        )


@router.post("/{game_id}/restart", response_model=GameResponse)
async def restart_game_endpoint(
    game_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GameResponse:
    """Restart a game."""
    try:
        game = await restart_game(db, game_id, current_user.id)
        return GameResponse(**build_game_response(game))
    except GameNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": str(e)},
        )
    except UnauthorizedGameAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden", "message": str(e)},
        )


@router.get("", response_model=list[GameResponse])
async def list_games(
    include_completed: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GameResponse]:
    """List all games for the current user."""
    games = await get_user_games(db, current_user.id, include_completed)
    return [GameResponse(**build_game_response(g)) for g in games]
