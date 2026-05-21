"""add difficulty to tic_tac_toe_games

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tic_tac_toe_games',
        sa.Column('difficulty', sa.String(length=10), nullable=False, server_default='medium')
    )


def downgrade() -> None:
    op.drop_column('tic_tac_toe_games', 'difficulty')
