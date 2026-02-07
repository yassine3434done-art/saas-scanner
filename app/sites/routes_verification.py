from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User
from app.sites.models import Site
from app.sites.ownership_models import OwnershipToken

router = APIRouter(prefix="/sites", tags=["sites"])

@router.get("/{site_id}/verification")
def get_verification(site_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    tok = db.query(OwnershipToken).filter(OwnershipToken.site_id == site.id).first()
    if not tok:
        raise HTTPException(status_code=500, detail="Token missing")

    token = tok.token
    return {
        "site_id": site.id,
        "url": site.url,
        "domain": site.domain,
        "methods": {
            "dns_txt_value": f"scanner-verification={token}",
            "file": {
                "path": "/.well-known/security-scanner.txt",
                "content": f"scanner-verification={token}",
                "full_url": site.url.rstrip("/") + "/.well-known/security-scanner.txt",
            },
            "meta_tag": f'<meta name="scanner-verification" content="{token}">'
        }
    }