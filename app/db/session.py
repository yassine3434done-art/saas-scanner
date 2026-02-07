# backend/app/db/session.py

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL


def _validate_db_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Set it in backend/.env or your environment.")

    # accept sqlite / postgres
    if not (url.startswith("sqlite") or url.startswith("postgresql")):
        raise RuntimeError(f"Invalid DATABASE_URL scheme: {url!r}")

    return url


DB_URL = _validate_db_url(DATABASE_URL)

connect_args = {}
if DB_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()