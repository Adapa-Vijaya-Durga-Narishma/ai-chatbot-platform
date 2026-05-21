"""
TicTacToeGame ORM model — pure data container, no logic.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TicTacToeGame(Base):
    __tablename__ = "tic_tac_toe_games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Board state as JSON: [["X", "", "O"], ["", "X", ""], ["O", "", ""]]
    board_state: Mapped[list[list[str]]] = mapped_column(
        JSON, nullable=False, default=[["", "", ""], ["", "", ""], ["", "", ""]]
    )
    # "X" or "O"
    current_turn: Mapped[str] = mapped_column(String(1), nullable=False, default="X")
    # "in_progress", "completed", "draw"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    # "X", "O", or None
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # "easy", "medium", "hard" (hard = unbeatable minimax)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="tic_tac_toe_games")  # noqa: F821
