from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import secrets
from datetime import datetime, timezone

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User

from app.sites.models import Site
from app.sites.ownership_models import OwnershipToken
from app.sites.verify import verify_dns_txt, verify_well_known, verify_meta
from app.plans.limits import get_user_plan

router = APIRouter(prefix="/sites", tags=["sites"])


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Empty URL")
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw
    p = urlparse(raw)
    if not p.hostname:
        raise ValueError("Invalid URL")
    path = p.path or "/"
    return f"{p.scheme}://{p.netloc}{path}"


def extract_domain(url: str) -> str:
    p = urlparse(url)
    if not p.hostname:
        raise ValueError("Invalid domain")
    return p.hostname.lower().strip(".")


def ensure_ownership_token(db: Session, site: Site) -> OwnershipToken:
    tok = db.query(OwnershipToken).filter(OwnershipToken.site_id == site.id).first()
    if tok:
        return tok
    token = secrets.token_hex(16)
    tok = OwnershipToken(site_id=site.id, token=token)
    db.add(tok)
    db.commit()
    db.refresh(tok)
    return tok


def verification_payload(site: Site, tok: OwnershipToken) -> dict:
    return {
        "site_id": site.id,
        "url": site.url,
        "domain": site.domain,
        "methods": {
            "dns_txt_value": f"scanner-verification={tok.token}",
            "file": {
                "path": "/.well-known/security-scanner.txt",
                "content": f"scanner-verification={tok.token}",
                "full_url": site.url.rstrip("/") + "/.well-known/security-scanner.txt",
            },
            "meta_tag": f'<meta name="scanner-verification" content="{tok.token}">',
        },
    }


@router.post("")
def create_site(url: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        url_n = normalize_url(url)
        domain = extract_domain(url_n)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    plan = get_user_plan(db, user)

    existing = db.query(Site).filter(Site.user_id == user.id).count()
    if existing >= int(plan.max_sites or 0):
        raise HTTPException(status_code=403, detail="Site limit reached for current plan")

    site = Site(user_id=user.id, url=url_n, domain=domain, is_verified=False)
    db.add(site)
    db.commit()
    db.refresh(site)

    tok = ensure_ownership_token(db, site)
    return {"site_id": site.id, "url": site.url, "verification": verification_payload(site, tok)}


@router.get("")
def list_sites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sites = db.query(Site).filter(Site.user_id == user.id).order_by(Site.id.desc()).all()

    items = [
        {
            "id": s.id,
            "url": s.url,
            "domain": s.domain,
            "is_verified": s.is_verified,
            "verified_at": s.verified_at,
        }
        for s in sites
    ]

    return {"value": items, "count": len(items)}


@router.get("/{site_id}/verification")
def get_verification(site_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    tok = ensure_ownership_token(db, site)
    return verification_payload(site, tok)


@router.post("/{site_id}/verify")
def verify_site(site_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    tok = ensure_ownership_token(db, site)

    dns_ok = verify_dns_txt(site.domain, tok.token)
    wk_ok = verify_well_known(site.url, tok.token)
    meta_ok = verify_meta(site.url, tok.token)

    ok = dns_ok or wk_ok or meta_ok

    if ok and not site.is_verified:
        site.is_verified = True
        site.verified_at = datetime.now(timezone.utc)
        db.commit()

    return {"verified": ok, "checks": {"dns_txt": dns_ok, "well_known_file": wk_ok, "meta_tag": meta_ok}}