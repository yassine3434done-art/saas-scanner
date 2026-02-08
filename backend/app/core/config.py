# backend/app/core/config.py

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv


def _load_env():
    """
    Load .env from backend root (works locally + on Render where env vars exist anyway).
    We don't override existing OS env vars.
    """
    # This file: backend/app/core/config.py  -> parents[2] = backend/
    backend_dir = Path(__file__).resolve().parents[2]
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    else:
        # fallback: try current working directory
        load_dotenv(override=False)


_load_env()


def _clean(s: str | None) -> str:
    s = (s or "").strip()
    # remove wrapping quotes if present
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    return s


DATABASE_URL = _clean(os.getenv("DATABASE_URL")) or "sqlite:///./scanner.db"

# Helpful local fallback: if user kept docker hostname "db", replace with localhost
if DATABASE_URL.startswith("postgresql://") and "@db:" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("@db:", "@localhost:")

JWT_SECRET = _clean(os.getenv("JWT_SECRET")) or "dev-secret"

try:
    JWT_EXPIRE_MIN = int(_clean(os.getenv("JWT_EXPIRE_MIN")) or "30")
except ValueError:
    JWT_EXPIRE_MIN = 30