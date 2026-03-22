"""drop_sequences_table

Revision ID: d523983781fd
Revises: ce0b38a4532b
Create Date: 2026-03-22 09:49:02.069515

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd523983781fd'
down_revision: Union[str, None] = 'ce0b38a4532b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('sequences')


def downgrade() -> None:
    op.create_table(
        'sequences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
