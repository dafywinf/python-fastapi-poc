"""Root conftest — sets required environment variables before test collection.

backend.config.Settings is a module-level singleton that reads from
os.environ at import time.  These values must be in place before any
backend module is imported, which happens when tests/conftest.py is loaded.
"""

import os

import bcrypt  # pyright: ignore[reportMissingModuleSource]

_TEST_PASSWORD = "testpass"
_hash: str = bcrypt.hashpw(  # pyright: ignore[reportUnknownMemberType]
    _TEST_PASSWORD.encode(),
    bcrypt.gensalt(rounds=4),  # pyright: ignore[reportUnknownMemberType]
).decode()

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use")
os.environ.setdefault("ADMIN_PASSWORD_HASH", _hash)
# Provide a placeholder DATABASE_URL so Settings() can be instantiated in
# environments where no .env file is present (e.g. CI before the
# testcontainers engine fixture overrides it).
os.environ.setdefault("DATABASE_URL", "postgresql://placeholder/placeholder")
