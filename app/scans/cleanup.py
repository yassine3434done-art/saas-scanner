from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.scans.models import Scan


def auto_cleanup_scans(
    db: Session,
    queued_ttl_minutes: int = 15,
    running_ttl_minutes: int = 60,
) -> dict:
    """
    - Mark stale queued scans as failed (queued + no started_at + too old)
    - Mark stale running scans as failed (running + started_at too old)
    """

    now = datetime.now(timezone.utc)
    queued_cutoff = now - timedelta(minutes=queued_ttl_minutes)
    running_cutoff = now - timedelta(minutes=running_ttl_minutes)

    fixed_queued = 0
    fixed_running = 0

    # A) queued stale
    queued = (
        db.query(Scan)
        .filter(Scan.status == "queued")
        .filter(Scan.started_at.is_(None))
        .all()
    )

    for s in queued:
        created = s.created_at
        if not created:
            continue

        # SQLite ممكن يرجّع naive datetime -> كنعتابرو UTC
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        if created <= queued_cutoff:
            s.status = "failed"
            s.error = "stale queued scan (auto-cleanup on startup)"
            s.finished_at = now
            fixed_queued += 1

    # B) running stale
    running = (
        db.query(Scan)
        .filter(Scan.status == "running")
        .filter(Scan.started_at.isnot(None))
        .all()
    )

    for s in running:
        started = s.started_at
        if not started:
            continue

        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        if started <= running_cutoff:
            s.status = "failed"
            s.error = "stale running scan (auto-timeout on startup)"
            s.finished_at = now
            fixed_running += 1

    if fixed_queued or fixed_running:
        db.commit()

    return {
        "fixed_queued": fixed_queued,
        "fixed_running": fixed_running,
        "queued_ttl_minutes": queued_ttl_minutes,
        "running_ttl_minutes": running_ttl_minutes,
    }