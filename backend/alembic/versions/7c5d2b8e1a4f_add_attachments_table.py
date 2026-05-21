"""add attachments table

Revision ID: 7c5d2b8e1a4f
Revises: 3c1b8cb0a2b1
Create Date: 2026-05-09

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7c5d2b8e1a4f"
down_revision: Union[str, None] = "3c1b8cb0a2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"], unique=False)
    op.create_index("ix_attachments_mime_type", "attachments", ["mime_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attachments_mime_type", table_name="attachments")
    op.drop_index("ix_attachments_message_id", table_name="attachments")
    op.drop_table("attachments")
