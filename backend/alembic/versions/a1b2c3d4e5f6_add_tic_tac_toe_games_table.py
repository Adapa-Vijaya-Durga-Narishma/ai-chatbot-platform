"""add tic_tac_toe_games table

Revision ID: a1b2c3d4e5f6
Revises: 7c5d2b8e1a4f
Create Date: 2026-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7c5d2b8e1a4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tic_tac_toe_games',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('board_state', postgresql.JSON(), nullable=False),
        sa.Column('current_turn', sa.String(length=1), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('winner', sa.String(length=1), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tic_tac_toe_games_user_id', 'tic_tac_toe_games', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_tic_tac_toe_games_user_id', table_name='tic_tac_toe_games')
    op.drop_table('tic_tac_toe_games')
