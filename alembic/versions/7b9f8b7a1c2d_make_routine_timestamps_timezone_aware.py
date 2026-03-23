"""make_routine_timestamps_timezone_aware

Revision ID: 7b9f8b7a1c2d
Revises: d523983781fd
Create Date: 2026-03-22 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b9f8b7a1c2d"
down_revision: Union[str, None] = "d523983781fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "routines",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "routine_executions",
        "started_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "routine_executions",
        "completed_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "routine_executions",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "routine_executions",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
        postgresql_using="started_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "routines",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        existing_server_default=sa.text("now()"),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
