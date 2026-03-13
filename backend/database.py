"""Database engine and session configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def get_session() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed after use.

    Yields:
        Session: A SQLAlchemy synchronous session.
    """
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
