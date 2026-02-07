# backend/app/scans/routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User
from app.sites.models import Site
from app.scans.models import Scan
from app.plans.limits import get_user_plan

router = APIRouter(prefix="/scans", tags=["scans"])


FREE_SCANS_PER_24H = 3
PAID_SCANS_PER_24H = 200


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt):
    dt = _as_utc(dt)
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _latest_scan(db: Session, *, user_id: int, site_id: int, scan_type: str):
    return (
        db.query(Scan)
        .filter(
            Scan.user_id == user_id,
            Scan.site_id == site_id,
            Scan.scan_type == scan_type,
        )
        .order_by(desc(Scan.id))
        .first()
    )


def _enforce_rate_limit_24h(db: Session, user: User, plan):
    """
    Free: 3 scans / 24h
    Paid: 200 scans / 24h
    (count all scan types)
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # SQLite might store naive dt; simplest: fetch recent N and count in python
    recent = (
        db.query(Scan)
        .filter(Scan.user_id == user.id)
        .order_by(desc(Scan.id))
        .limit(500)  # safe cap
        .all()
    )

    used = 0
    for s in recent:
        created = _as_utc(s.created_at)
        if created and created >= cutoff:
            used += 1

    limit = FREE_SCANS_PER_24H if plan.name == "free" else PAID_SCANS_PER_24H
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {limit} scans per 24h (used={used}).",
        )


@router.post("/sites/{site_id}/public")
def enqueue_public_scan(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    plan = get_user_plan(db, user)

    # ✅ rate limit (free/paid)
    _enforce_rate_limit_24h(db, user, plan)

    # Free retest cooldown (30min) based on last PUBLIC scan time
    if plan.name == "free":
        last = _latest_scan(db, user_id=user.id, site_id=site.id, scan_type="public")
        if last and last.created_at:
            created = _as_utc(last.created_at)
            if (datetime.now(timezone.utc) - created) < timedelta(minutes=30):
                raise HTTPException(
                    status_code=429,
                    detail="Retest cooldown: wait 30 minutes on Free plan",
                )

    scan = Scan(
        user_id=user.id,
        site_id=site.id,
        scan_type="public",
        status="queued",
        started_at=None,
        finished_at=None,
        summary=None,
        error=None,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return {"scan_id": scan.id, "status": scan.status, "created_at": _iso(scan.created_at)}


@router.post("/sites/{site_id}/advanced")
def enqueue_advanced_scan(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    if not site.is_verified:
        raise HTTPException(status_code=403, detail="Site must be verified before advanced scans")

    plan = get_user_plan(db, user)
    if plan.name == "free":
        raise HTTPException(status_code=403, detail="Advanced scans are not available on Free plan")

    # ✅ rate limit (paid too)
    _enforce_rate_limit_24h(db, user, plan)

    # optional short cooldown (20s) based on last ADVANCED scan time
    last_adv = _latest_scan(db, user_id=user.id, site_id=site.id, scan_type="advanced")
    if last_adv and last_adv.created_at:
        created = _as_utc(last_adv.created_at)
        if (datetime.now(timezone.utc) - created) < timedelta(seconds=20):
            raise HTTPException(status_code=429, detail="Advanced scan cooldown: wait 20 seconds")

    scan = Scan(
        user_id=user.id,
        site_id=site.id,
        scan_type="advanced",
        status="queued",
        started_at=None,
        finished_at=None,
        summary=None,
        error=None,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return {"scan_id": scan.id, "status": scan.status, "created_at": _iso(scan.created_at)}


@router.get("")
def list_scans(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    scans = (
        db.query(Scan)
        .filter(Scan.user_id == user.id, Scan.site_id == site.id)
        .order_by(Scan.id.desc())
        .all()
    )

    items = [
        {
            "id": s.id,
            "status": s.status,
            "scan_type": s.scan_type,
            "created_at": _iso(s.created_at),
            "started_at": _iso(s.started_at),
            "finished_at": _iso(s.finished_at),
            "summary": s.summary,
            "error": s.error,
        }
        for s in scans
    ]

    return {"value": items, "count": len(items)}


@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    s = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "id": s.id,
        "status": s.status,
        "scan_type": s.scan_type,
        "created_at": _iso(s.created_at),
        "started_at": _iso(s.started_at),
        "finished_at": _iso(s.finished_at),
        "summary": s.summary,
        "error": s.error,
    }