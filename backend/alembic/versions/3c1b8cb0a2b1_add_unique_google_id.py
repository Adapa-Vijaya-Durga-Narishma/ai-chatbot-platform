"""add unique google_id

Revision ID: 3c1b8cb0a2b1
Revises: 9f90e6b9f5e2
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op


revision: str = "3c1b8cb0a2b1"
down_revision: Union[str, None] = "9f90e6b9f5e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
