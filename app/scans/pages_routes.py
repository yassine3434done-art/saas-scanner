from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timezone

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User
from app.scans.models import Scan
from app.scans.pages_models import ScanPage

router = APIRouter(prefix="/scans", tags=["scans"])


def _iso(dt):
    if dt is None:
        return None
    # SQLite can return naive -> treat as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


@router.get("/{scan_id}/pages")
def list_scan_pages(
    scan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # تأكد scan ديال نفس user
    s = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    pages = (
        db.query(ScanPage)
        .filter(ScanPage.scan_id == scan_id)
        .order_by(ScanPage.id.asc())
        .all()
    )

    items = [
        {
            "id": p.id,
            "url": p.url,
            "status_code": p.status_code,
            "created_at": _iso(p.created_at),
        }
        for p in pages
    ]

    return {"scan_id": scan_id, "value": items, "count": len(items)}