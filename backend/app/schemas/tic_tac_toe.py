"""
Tic Tac Toe Pydantic schemas — separate from ORM models.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Request Schemas ───────────────────────────────────────────────────────────

class GameCreateRequest(BaseModel):
    """Request to create a new Tic Tac Toe game."""
    difficulty: str = Field(
        default="medium",
        pattern="^(easy|medium|hard)$",
        description="Difficulty level: 'easy' (LLM, makes mistakes), 'medium' (LLM, moderate), 'hard' (Minimax, unbeatable)"
    )


class PlayerMoveRequest(BaseModel):
    """Request to make a player move."""
    game_id: uuid.UUID
    row: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column index (0-2)")


# ── Response Schemas ──────────────────────────────────────────────────────────

class BoardStateResponse(BaseModel):
    """Current board state representation."""
    board: list[list[str]] = Field(
        ...,
        description="3x3 board where each cell is 'X', 'O', or ''",
        examples=[[["X", "", "O"], ["", "X", ""], ["O", "", ""]]]
    )
    current_turn: str = Field(..., description="Whose turn: 'X' or 'O'")
    available_moves: list[tuple[int, int]] = Field(
        default_factory=list,
        description="List of (row, col) tuples for available moves"
    )


class GameResponse(BaseModel):
    """Full game state response."""
    id: uuid.UUID
    board: list[list[str]]
    current_turn: str
    status: str = Field(..., description="'in_progress', 'completed', or 'draw'")
    winner: str | None = Field(None, description="'X', 'O', or None")
    player_symbol: str = Field(default="X", description="Human player's symbol")
    ai_symbol: str = Field(default="O", description="AI player's symbol")
    difficulty: str = Field(default="medium", description="Game difficulty level")
    available_moves: list[tuple[int, int]] = Field(default_factory=list)
    ai_reasoning: str | None = Field(None, description="AI's reasoning for its last move (LLM modes only)")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MoveResponse(BaseModel):
    """Response after a move is made."""
    game: GameResponse
    player_move: tuple[int, int] | None = Field(None, description="The player's move")
    ai_move: tuple[int, int] | None = Field(None, description="The AI's move (if applicable)")
    ai_reasoning: str | None = Field(None, description="AI's reasoning for its move (LLM modes only)")
    message: str = Field(default="", description="Status message")
    message: str = Field(default="", description="Status message")
