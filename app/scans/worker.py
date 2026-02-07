# backend/app/scans/worker.py

import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.scans.models import Scan
from app.sites.models import Site
from app.users.models import User
from app.plans.limits import get_user_plan
from app.plans.models import Plan

from app.scans.pages_models import ScanPage
from app.scans.public_scan import fetch_tls_info, public_headers_check, crawl_light
from app.ssrf.http import safe_get


def _claim_next_scan(db: Session) -> Scan | None:
    """
    Priority queue:
      1) Paid users (plan.priority_queue=True)
      2) Free users (FIFO)
    """
    paid_scan = (
        db.query(Scan)
        .join(User, User.id == Scan.user_id)
        .join(Plan, Plan.id == User.plan_id)
        .filter(Scan.status == "queued")
        .filter(Plan.priority_queue.is_(True))
        .order_by(Scan.id.asc())
        .first()
    )

    s = paid_scan
    if not s:
        s = (
            db.query(Scan)
            .filter(Scan.status == "queued")
            .order_by(Scan.id.asc())
            .first()
        )

    if not s:
        return None

    s.status = "running"
    s.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)
    return s


def _store_pages(db: Session, scan_id: int, pages: list[dict]):
    for p in pages or []:
        db.add(
            ScanPage(
                scan_id=scan_id,
                url=p.get("url"),
                status_code=int(p.get("status_code") or 0),
            )
        )
    db.commit()


def _get_site_and_plan(db: Session, scan: Scan) -> tuple[Site, object]:
    site = (
        db.query(Site)
        .filter(Site.id == scan.site_id, Site.user_id == scan.user_id)
        .first()
    )
    if not site:
        raise RuntimeError("Site not found for scan")

    user = db.query(User).filter(User.id == scan.user_id).first()
    if not user:
        raise RuntimeError("User not found for scan")

    plan = get_user_plan(db, user)
    return site, plan


def _compute_risk(findings: list[dict]) -> dict:
    weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}
    counts = {k: 0 for k in weights}

    for f in findings or []:
        sev = (f.get("severity") or "info").lower()
        if sev in counts:
            counts[sev] += 1

    score = min(
        100,
        sum(counts[s] * weights[s] for s in counts),
    )

    if score >= 80:
        label = "critical"
    elif score >= 50:
        label = "high"
    elif score >= 20:
        label = "medium"
    elif score > 0:
        label = "low"
    else:
        label = "info"

    return {"score": score, "label": label, "counts": counts}


def _run_public(db: Session, scan: Scan):
    site, plan = _get_site_and_plan(db, scan)

    resp = safe_get(site.url, timeout=10)
    headers_result = public_headers_check(resp)
    tls_result = fetch_tls_info(site.url)

    crawl_result = crawl_light(
        site.url,
        max_pages=int(plan.crawl_limit),
        max_seconds=int(plan.max_duration_min) * 60,
    )

    _store_pages(db, scan.id, crawl_result.get("pages", []))

    scan.summary = {
        "headers": headers_result,
        "tls": tls_result,
        "crawl": crawl_result.get("metrics", {}),
        "findings": [],
        "risk": {"score": 0, "label": "info", "counts": {}},
    }


def _run_advanced(db: Session, scan: Scan):
    _run_public(db, scan)

    summary = scan.summary or {}
    sec = (summary.get("headers") or {}).get("security_headers") or {}

    findings = []

    if not sec.get("content-security-policy"):
        findings.append(
            {
                "id": "missing_csp",
                "severity": "medium",
                "title": "Missing Content-Security-Policy",
                "evidence": "content-security-policy header not present",
            }
        )

    if not sec.get("x-frame-options"):
        findings.append(
            {
                "id": "missing_xfo",
                "severity": "low",
                "title": "Missing X-Frame-Options",
                "evidence": "x-frame-options header not present",
            }
        )

    summary["findings"] = findings
    summary["risk"] = _compute_risk(findings)
    summary["note"] = "Advanced scan is MVP-stub (no ZAP/nuclei/testssl yet)."
    scan.summary = summary


def _fail_scan(db: Session, scan_id: int, err: Exception):
    s = db.query(Scan).filter(Scan.id == scan_id).first()
    if not s:
        return
    s.status = "failed"
    s.error = (str(err) or "unknown error")[:500]
    s.finished_at = datetime.now(timezone.utc)
    db.commit()


def _run_one(scan_id: int):
    db = SessionLocal()
    try:
        s = db.query(Scan).filter(Scan.id == scan_id).first()
        if not s:
            return

        if s.scan_type == "public":
            _run_public(db, s)
        elif s.scan_type == "advanced":
            _run_advanced(db, s)
        else:
            raise RuntimeError(f"Unknown scan_type: {s.scan_type}")

        s.status = "done"
        s.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        _fail_scan(db, scan_id, e)
    finally:
        db.close()


async def scans_worker_loop(poll_seconds: float = 1.0):
    """
    Async loop + thread offloading
    """
    while True:
        db = SessionLocal()
        try:
            scan = _claim_next_scan(db)
        finally:
            db.close()

        if scan:
            await asyncio.to_thread(_run_one, scan.id)
        else:
            await asyncio.sleep(poll_seconds)