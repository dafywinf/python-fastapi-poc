"""make_actions_position_constraint_deferrable

Revision ID: ce0b38a4532b
Revises: 1c3823cf5e3b
Create Date: 2026-03-21 18:26:39.303966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce0b38a4532b'
down_revision: Union[str, None] = '1c3823cf5e3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing constraint (may be non-deferrable on databases created
    # before this fix) and recreate it as DEFERRABLE INITIALLY DEFERRED so that
    # position-swap operations can flush two UPDATEs without a mid-flush
    # uniqueness violation (constraint is only enforced at COMMIT time).
    op.execute("ALTER TABLE actions DROP CONSTRAINT IF EXISTS uq_actions_routine_position")
    op.execute(
        "ALTER TABLE actions ADD CONSTRAINT uq_actions_routine_position "
        "UNIQUE (routine_id, position) DEFERRABLE INITIALLY DEFERRED"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE actions DROP CONSTRAINT IF EXISTS uq_actions_routine_position")
    op.execute(
        "ALTER TABLE actions ADD CONSTRAINT uq_actions_routine_position "
        "UNIQUE (routine_id, position)"
    )
