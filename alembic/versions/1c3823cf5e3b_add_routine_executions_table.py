"""add_routine_executions_table

Revision ID: 1c3823cf5e3b
Revises: c64e0a7be9e1
Create Date: 2026-03-21 14:06:53.330554

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c3823cf5e3b'
down_revision: Union[str, None] = 'c64e0a7be9e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'routine_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('routine_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('triggered_by', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['routine_id'], ['routines.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute(
        "CREATE UNIQUE INDEX uix_routine_one_running ON routine_executions (routine_id) WHERE status = 'running'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uix_routine_one_running")
    op.drop_table('routine_executions')
