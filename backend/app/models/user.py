"""
User ORM model — pure data container, no methods or business logic.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship — back-populated from ChatThread
    threads: Mapped[list["ChatThread"]] = relationship(  # noqa: F821
        "ChatThread", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationship — back-populated from TicTacToeGame
    tic_tac_toe_games: Mapped[list["TicTacToeGame"]] = relationship(  # noqa: F821
        "TicTacToeGame", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_google_id", "google_id"),
    )
