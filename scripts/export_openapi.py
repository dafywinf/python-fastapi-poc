"""Export the FastAPI OpenAPI schema for frontend contract generation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./openapi-export.db")
os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-secret")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("ENABLE_PASSWORD_AUTH", "true")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: poetry run python scripts/export_openapi.py <output-path>")
        return 1

    output_path = Path(sys.argv[1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from backend.config import settings

    # Keep schema generation deterministic and isolated from local services.
    settings.database_url = "sqlite:///./openapi-export.db"
    settings.jwt_secret_key = "openapi-export-secret"
    settings.scheduler_enabled = False
    settings.enable_password_auth = True
    settings.loki_url = None

    from backend.main import app

    output_path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote OpenAPI schema to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
