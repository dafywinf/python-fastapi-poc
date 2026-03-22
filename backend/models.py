"""SQLAlchemy ORM models — source of truth for the database schema."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class User(Base):
    """Persisted Google account — created or updated on each OAuth login."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Routine(Base):
    """A home automation routine with a schedule and ordered actions."""

    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)
    schedule_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actions: Mapped[list["Action"]] = relationship(
        "Action",
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="Action.position",
    )
    executions: Mapped[list["RoutineExecution"]] = relationship(
        "RoutineExecution",
        back_populates="routine",
        cascade="all, delete-orphan",
    )


class Action(Base):
    """A single step within a Routine, executed in order by position."""

    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    routine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routines.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    routine: Mapped["Routine"] = relationship("Routine", back_populates="actions")


class RoutineExecution(Base):
    """A single execution record for a Routine."""

    __tablename__ = "routine_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    routine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("routines.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    routine: Mapped["Routine"] = relationship("Routine", back_populates="executions")
