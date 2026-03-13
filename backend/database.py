"""Database engine and session configuration."""

import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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
