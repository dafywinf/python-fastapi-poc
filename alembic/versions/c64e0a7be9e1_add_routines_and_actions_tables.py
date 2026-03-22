"""add_routines_and_actions_tables

Revision ID: c64e0a7be9e1
Revises: fb85d06b1459
Create Date: 2026-03-21 14:06:40.086741

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c64e0a7be9e1'
down_revision: Union[str, None] = 'fb85d06b1459'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'routines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('schedule_type', sa.String(), nullable=False),
        sa.Column('schedule_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('routine_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['routine_id'], ['routines.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Create the unique constraint as DEFERRABLE INITIALLY DEFERRED so that
    # position-swap operations (which temporarily violate uniqueness mid-flush)
    # are only checked at COMMIT time rather than after each individual UPDATE.
    op.execute(
        "ALTER TABLE actions ADD CONSTRAINT uq_actions_routine_position "
        "UNIQUE (routine_id, position) DEFERRABLE INITIALLY DEFERRED"
    )


def downgrade() -> None:
    op.drop_constraint('uq_actions_routine_position', 'actions')
    op.drop_table('actions')
    op.drop_table('routines')
