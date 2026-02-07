from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User
from app.scans.models import Scan

router = APIRouter(prefix="/scans", tags=["scans"])

@router.get("/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "id": s.id,
        "status": s.status,
        "scan_type": s.scan_type,
        "created_at": s.created_at,
        "started_at": s.started_at,
        "finished_at": s.finished_at,
        "summary": s.summary,
        "error": s.error,
    }