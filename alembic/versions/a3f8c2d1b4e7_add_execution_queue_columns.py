"""add_execution_queue_columns

Revision ID: a3f8c2d1b4e7
Revises: e4f3a2b1c0d9
Create Date: 2026-04-25 00:00:00.000000

Adds queued_at and scheduled_for to routine_executions, makes started_at
nullable (it now records actual execution start rather than insert time),
drops the per-routine uniqueness constraint so multiple runs can queue up,
and adds a partial index for efficient queue polling.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3f8c2d1b4e7"
down_revision: Union[str, None] = "e4f3a2b1c0d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add queued_at — backfill from started_at for existing rows
    op.add_column(
        "routine_executions",
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("UPDATE routine_executions SET queued_at = started_at")

    # 2. Add scheduled_for — backfill from started_at for existing rows
    op.add_column(
        "routine_executions",
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute("UPDATE routine_executions SET scheduled_for = started_at")

    # 3. started_at is now set by the queue worker when execution begins,
    #    so it must be nullable (queued rows have no started_at yet)
    op.alter_column(
        "routine_executions",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    # 4. Drop the per-routine uniqueness constraint — queue allows multiple
    #    runs of the same routine to wait in line
    op.execute("DROP INDEX IF EXISTS uix_routine_one_running")

    # 5. Partial index for efficient queue polling:
    #    SELECT ... WHERE status='queued' AND scheduled_for <= now()
    op.execute(
        "CREATE INDEX ix_routine_executions_queue "
        "ON routine_executions (scheduled_for) "
        "WHERE status = 'queued'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_routine_executions_queue")
    op.execute(
        "CREATE UNIQUE INDEX uix_routine_one_running "
        "ON routine_executions (routine_id) WHERE status = 'running'"
    )
    op.alter_column(
        "routine_executions",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_column("routine_executions", "scheduled_for")
    op.drop_column("routine_executions", "queued_at")
