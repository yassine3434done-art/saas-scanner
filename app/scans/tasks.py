from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.celery_app import celery
from app.db.session import SessionLocal
from app.scans.models import Scan
from app.scans.pages_models import ScanPage
from app.scans.public_scan import fetch_tls_info, public_headers_check, crawl_light
from app.ssrf.http import safe_get
from app.plans.models import Plan
from app.users.models import User

@celery.task(name="public_scan_task")
def public_scan_task(scan_id: int):
    db: Session = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return {"ok": False, "error": "scan not found"}

        user = db.query(User).filter(User.id == scan.user_id).first()
        if not user:
            scan.status = "failed"
            scan.error = "user not found"
            db.commit()
            return {"ok": False, "error": scan.error}

        plan = db.query(Plan).filter(Plan.id == user.plan_id).first()
        if not plan:
            scan.status = "failed"
            scan.error = "plan missing"
            db.commit()
            return {"ok": False, "error": scan.error}

        # mark running
        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        # Fetch target URL from DB via site relation (small extra query)
        # (Avoid importing Site here to keep task light; use raw query if you prefer)
        from app.sites.models import Site  # local import
        site = db.query(Site).filter(Site.id == scan.site_id, Site.user_id == scan.user_id).first()
        if not site:
            scan.status = "failed"
            scan.error = "site not found"
            scan.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"ok": False, "error": scan.error}

        resp = safe_get(site.url, timeout=10)
        headers_result = public_headers_check(resp)
        tls_result = fetch_tls_info(site.url)

        max_pages = int(plan.crawl_limit)
        max_seconds = int(plan.max_duration_min) * 60
        crawl_result = crawl_light(site.url, max_pages=max_pages, max_seconds=max_seconds)

        # store pages
        for p in crawl_result["pages"]:
            db.add(ScanPage(scan_id=scan.id, url=p["url"], status_code=p["status_code"]))
        db.commit()

        scan.summary = {
            "headers": headers_result,
            "tls": tls_result,
            "crawl": crawl_result["metrics"],
        }
        scan.status = "done"
        scan.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"ok": True, "scan_id": scan.id}

    except Exception as e:
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = "failed"
                scan.error = str(e)[:500]
                scan.finished_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            return {"ok": False, "error": str(e)[:200]}
    finally:
        db.close()