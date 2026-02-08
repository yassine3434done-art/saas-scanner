# backend/app/reports/routes.py

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta
import secrets
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

from app.db.session import get_db
from app.auth.deps import get_current_user
from app.users.models import User
from app.scans.models import Scan
from app.sites.models import Site
from app.scans.pages_models import ScanPage
from app.plans.limits import get_user_plan

from app.reports.models import ReportEvent, ReportShareLink
from app.email.resend_client import send_email, EmailSendError

# ✅ Rate limiting (slowapi)
from app.core.ratelimit import limiter

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------------- helpers ----------------

def _as_utc(dt):
    if not dt:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _fmt(dt):
    dt = _as_utc(dt)
    if not dt:
        return "-"
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _wrap_text(c: canvas.Canvas, text: str, max_width: float, font="Helvetica", size=10):
    c.setFont(font, size)
    s = str(text or "-")
    words = s.split()
    if not words:
        return ["-"]

    lines = []
    line = ""

    def push_line(x):
        if x:
            lines.append(x)

    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, font, size) <= max_width:
            line = t
        else:
            if not line:
                chunk = ""
                for ch in w:
                    if c.stringWidth(chunk + ch, font, size) <= max_width:
                        chunk += ch
                    else:
                        push_line(chunk)
                        chunk = ch
                push_line(chunk)
                line = ""
            else:
                push_line(line)
                line = w

    push_line(line)
    return lines or ["-"]


def _draw_kv(c: canvas.Canvas, x, y, k, v, page_width, right_margin):
    key_w = 110
    max_val_w = (page_width - right_margin) - (x + key_w)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, f"{k}:")

    c.setFont("Helvetica", 10)
    lines = _wrap_text(c, "-" if v is None else v, max_val_w, font="Helvetica", size=10)

    yy = y
    for ln in lines:
        c.drawString(x + key_w, yy, ln)
        yy -= 0.5 * cm

    return yy


def _require_finished(scan: Scan):
    if scan.status not in ("done", "failed"):
        raise HTTPException(status_code=409, detail="Scan is not finished yet")


def _enforce_history_policy(db: Session, user: User, plan, scan: Scan):
    # Free: allow_history=False => only latest scan for that site
    if plan.allow_history:
        return

    latest_scan = (
        db.query(Scan)
        .filter(Scan.user_id == user.id, Scan.site_id == scan.site_id)
        .order_by(desc(Scan.id))
        .first()
    )
    if not latest_scan or latest_scan.id != scan.id:
        raise HTTPException(
            status_code=403,
            detail="History is not available on Free plan (only latest scan)",
        )


def _enforce_report_quota(db: Session, user: User, plan, *, kind: str):
    """
    Free: 3 PDFs / 24h
    Paid: 200 PDFs / 24h
    Paid email: 50 / 24h (kind="pdf_email")
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)

    used = (
        db.query(ReportEvent)
        .filter(ReportEvent.user_id == user.id)
        .filter(ReportEvent.kind == kind)
        .filter(ReportEvent.created_at >= window_start)
        .count()
    )

    if kind == "pdf_email":
        limit = 0 if plan.name == "free" else 50
    else:
        limit = 3 if plan.name == "free" else 200

    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Report limit reached: {limit} per 24h on your plan",
        )


def _log_report_event(db: Session, user_id: int, scan_id: int | None, kind: str):
    db.add(ReportEvent(user_id=user_id, scan_id=scan_id, kind=kind))
    db.commit()


def _sev_rank(sev: str | None) -> int:
    s = (sev or "").strip().lower()
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}.get(s, 0)


def _sorted_findings(findings: list[dict]) -> list[dict]:
    return sorted(
        findings or [],
        key=lambda f: (
            -_sev_rank((f or {}).get("severity")),
            str((f or {}).get("id") or ""),
            str((f or {}).get("title") or ""),
        ),
    )


def _top_fixes(sec_headers: dict, findings_sorted: list[dict], limit: int = 3) -> list[str]:
    """
    Generate short actionable fixes (Top N) from findings + missing security headers.
    Uses findings severity ordering already applied in findings_sorted.
    """
    fixes: list[str] = []

    id_to_fix = {
        "missing_csp": "Add a strong Content-Security-Policy (CSP) header.",
        "missing_xfo": "Add X-Frame-Options (or CSP frame-ancestors) to prevent clickjacking.",
        "missing_hsts": "Enable HSTS (Strict-Transport-Security) to force HTTPS.",
        "missing_xcto": "Add X-Content-Type-Options: nosniff.",
        "missing_referrer_policy": "Add Referrer-Policy (e.g., strict-origin-when-cross-origin).",
        "missing_permissions_policy": "Add Permissions-Policy to restrict powerful browser features.",
    }

    # A) map known finding IDs
    for f in findings_sorted or []:
        fid = (f or {}).get("id")
        if fid in id_to_fix:
            fixes.append(id_to_fix[fid])

    # B) fallback from missing headers
    sec_headers = sec_headers or {}
    if not sec_headers.get("content-security-policy"):
        fixes.append("Add a strong Content-Security-Policy (CSP) header.")
    if not sec_headers.get("x-frame-options"):
        fixes.append("Add X-Frame-Options (or CSP frame-ancestors) to prevent clickjacking.")
    if not sec_headers.get("x-content-type-options"):
        fixes.append("Add X-Content-Type-Options: nosniff.")
    if not sec_headers.get("referrer-policy"):
        fixes.append("Add Referrer-Policy (e.g., strict-origin-when-cross-origin).")
    if not sec_headers.get("permissions-policy"):
        fixes.append("Add Permissions-Policy to restrict powerful browser features.")

    # unique while preserving order
    uniq: list[str] = []
    for x in fixes:
        if x not in uniq:
            uniq.append(x)

    return uniq[: max(0, int(limit))]


def _build_pdf_bytes(
    *,
    plan_name: str,
    scan: Scan,
    site: Site,
    sec_headers: dict,
    tls: dict,
    crawl: dict,
    findings: list,
    pages: list[ScanPage],
    include_pages: bool,
) -> bytes:
    import io

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    left = 2 * cm
    right = 2 * cm
    y = h - 2 * cm

    def ensure_space(min_y=2.5 * cm):
        nonlocal y
        if y < min_y:
            c.showPage()
            y = h - 2 * cm

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "SaaS Scanner Report")
    y -= 1.2 * cm

    # Meta
    y = _draw_kv(c, left, y, "Plan", plan_name, w, right)
    y = _draw_kv(c, left, y, "Scan ID", scan.id, w, right)
    y = _draw_kv(c, left, y, "Type", scan.scan_type, w, right)
    y = _draw_kv(c, left, y, "Status", scan.status, w, right)
    y = _draw_kv(c, left, y, "Created", _fmt(scan.created_at), w, right)
    y = _draw_kv(c, left, y, "Started", _fmt(scan.started_at), w, right)
    y = _draw_kv(c, left, y, "Finished", _fmt(scan.finished_at), w, right)

    y -= 0.2 * cm
    ensure_space()

    # Site
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Site")
    y -= 0.8 * cm

    y = _draw_kv(c, left, y, "URL", site.url, w, right)
    y = _draw_kv(c, left, y, "Domain", site.domain, w, right)
    y = _draw_kv(c, left, y, "Verified", str(bool(site.is_verified)), w, right)
    y = _draw_kv(c, left, y, "Verified At", _fmt(site.verified_at), w, right)

    y -= 0.2 * cm
    ensure_space()

    # Security Headers
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Security Headers")
    y -= 0.8 * cm
    for k in [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
    ]:
        ensure_space()
        y = _draw_kv(c, left, y, k, (sec_headers or {}).get(k) or "-", w, right)

    y -= 0.2 * cm
    ensure_space()

    # TLS
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "TLS")
    y -= 0.8 * cm
    for k in ["enabled", "protocol", "cipher", "notBefore", "notAfter"]:
        ensure_space()
        y = _draw_kv(c, left, y, k, tls.get(k) if tls.get(k) is not None else "-", w, right)

    y -= 0.2 * cm
    ensure_space()

    # Crawl
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Crawl")
    y -= 0.8 * cm
    for k in ["visited", "unique_seen", "time_spent_sec"]:
        ensure_space()
        y = _draw_kv(c, left, y, k, crawl.get(k) if crawl.get(k) is not None else "-", w, right)

    y -= 0.2 * cm
    ensure_space()

    # Risk Score (optional)
    summary = scan.summary or {}
    risk = summary.get("risk") or {}
    score = risk.get("score", 0)
    label = risk.get("label", "-")
    counts = risk.get("counts") or {}

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Risk Score")
    y -= 0.8 * cm

    y = _draw_kv(c, left, y, "Score (0-100)", score, w, right)
    y = _draw_kv(c, left, y, "Level", label, w, right)
    cnt_line = " / ".join([f"{k}:{counts.get(k,0)}" for k in ["critical", "high", "medium", "low", "info"]])
    y = _draw_kv(c, left, y, "Counts", cnt_line, w, right)

    y -= 0.2 * cm
    ensure_space()

    # Findings (sorted)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Findings (sorted)")
    y -= 0.8 * cm

    findings_sorted = _sorted_findings(findings or [])

    if not findings_sorted:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, "- none -")
        y -= 0.6 * cm
    else:
        c.setFont("Helvetica", 10)
        for f in findings_sorted:
            ensure_space()
            sev = (f.get("severity") or "info").lower()
            line = f"- [{sev}] {f.get('title')} ({f.get('id')})"
            c.drawString(left, y, line)
            y -= 0.55 * cm

            ev = f.get("evidence") or "-"
            for ln in _wrap_text(c, f"evidence: {ev}", max_width=(w - right - left), font="Helvetica", size=10):
                ensure_space()
                c.drawString(left + 0.3 * cm, y, ln)
                y -= 0.55 * cm

            y -= 0.2 * cm

    # ✅ Top Fixes (short)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Top Fixes")
    y -= 0.8 * cm

    fixes = _top_fixes(sec_headers or {}, findings_sorted, limit=3)

    c.setFont("Helvetica", 10)
    if not fixes:
        c.drawString(left, y, "- none -")
        y -= 0.6 * cm
    else:
        for fx in fixes:
            ensure_space()
            for ln in _wrap_text(c, f"- {fx}", max_width=(w - right - left), font="Helvetica", size=10):
                ensure_space()
                c.drawString(left, y, ln)
                y -= 0.55 * cm
            y -= 0.1 * cm

    y -= 0.2 * cm
    ensure_space()

    # Paid appendix: pages
    if include_pages:
        c.showPage()
        y = h - 2 * cm

        c.setFont("Helvetica-Bold", 14)
        c.drawString(left, y, "Appendix: Pages")
        y -= 1.0 * cm

        c.setFont("Helvetica", 10)
        if not pages:
            c.drawString(left, y, "- none -")
        else:
            for p in pages:
                ensure_space()
                line = f"{p.status_code or '-'}  {p.url}"
                for ln in _wrap_text(c, line, max_width=(w - right - left), font="Helvetica", size=10):
                    ensure_space()
                    c.drawString(left, y, ln)
                    y -= 0.5 * cm

    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def _resolve_scan_for_pdf(
    db: Session,
    user: User,
    scan_id: int | None,
    site_id: int | None,
    latest: bool,
) -> Scan:
    if scan_id is not None:
        scan = db.query(Scan).filter(Scan.id == scan_id, Scan.user_id == user.id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        return scan

    if site_id is not None:
        q = db.query(Scan).filter(Scan.user_id == user.id, Scan.site_id == site_id)
        q = q.order_by(desc(Scan.id)) if latest else q.order_by(Scan.id.asc())
        scan = q.first()
        if not scan:
            raise HTTPException(status_code=404, detail="No scans found for this site")
        return scan

    raise HTTPException(status_code=400, detail="Provide scan_id or site_id")


def _render_pdf_response(pdf: bytes, *, scan_id: int, as_attachment: bool):
    dispo = "attachment" if as_attachment else "inline"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{dispo}; filename="scan-{scan_id}.pdf"'},
    )


def _create_share_link(db: Session, *, user_id: int, scan_id: int, ttl_minutes: int = 15) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    db.add(ReportShareLink(token=token, user_id=user_id, scan_id=scan_id, expires_at=expires_at))
    db.commit()
    return token


# ---------------- routes ----------------

@router.get("/pdf")
def report_pdf(
    scan_id: int | None = Query(default=None),
    site_id: int | None = Query(default=None),
    latest: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = get_user_plan(db, user)
    _enforce_report_quota(db, user, plan, kind="pdf")

    scan = _resolve_scan_for_pdf(db, user, scan_id=scan_id, site_id=site_id, latest=latest)
    _require_finished(scan)
    _enforce_history_policy(db, user, plan, scan)

    site = db.query(Site).filter(Site.id == scan.site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    summary = scan.summary or {}
    headers = summary.get("headers") or {}
    sec_headers = headers.get("security_headers") or {}
    tls = summary.get("tls") or {}
    crawl = summary.get("crawl") or {}
    findings = summary.get("findings") or []

    include_pages = bool(plan.allow_history)  # paid only
    pages: list[ScanPage] = []
    if include_pages:
        pages = (
            db.query(ScanPage)
            .filter(ScanPage.scan_id == scan.id)
            .order_by(ScanPage.id.asc())
            .all()
        )

    pdf = _build_pdf_bytes(
        plan_name=plan.name,
        scan=scan,
        site=site,
        sec_headers=sec_headers,
        tls=tls,
        crawl=crawl,
        findings=findings,
        pages=pages,
        include_pages=include_pages,
    )

    _log_report_event(db, user_id=user.id, scan_id=scan.id, kind="pdf")
    return _render_pdf_response(pdf, scan_id=scan.id, as_attachment=False)


@router.get("/pdf/download")
def report_pdf_download(
    scan_id: int | None = Query(default=None),
    site_id: int | None = Query(default=None),
    latest: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = get_user_plan(db, user)
    _enforce_report_quota(db, user, plan, kind="pdf_download")

    scan = _resolve_scan_for_pdf(db, user, scan_id=scan_id, site_id=site_id, latest=latest)
    _require_finished(scan)
    _enforce_history_policy(db, user, plan, scan)

    site = db.query(Site).filter(Site.id == scan.site_id, Site.user_id == user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    summary = scan.summary or {}
    headers = summary.get("headers") or {}
    sec_headers = headers.get("security_headers") or {}
    tls = summary.get("tls") or {}
    crawl = summary.get("crawl") or {}
    findings = summary.get("findings") or []

    include_pages = bool(plan.allow_history)  # paid only
    pages: list[ScanPage] = []
    if include_pages:
        pages = (
            db.query(ScanPage)
            .filter(ScanPage.scan_id == scan.id)
            .order_by(ScanPage.id.asc())
            .all()
        )

    pdf = _build_pdf_bytes(
        plan_name=plan.name,
        scan=scan,
        site=site,
        sec_headers=sec_headers,
        tls=tls,
        crawl=crawl,
        findings=findings,
        pages=pages,
        include_pages=include_pages,
    )

    _log_report_event(db, user_id=user.id, scan_id=scan.id, kind="pdf_download")
    return _render_pdf_response(pdf, scan_id=scan.id, as_attachment=True)


@router.head("/pdf")
def report_pdf_head(
    scan_id: int | None = Query(default=None),
    site_id: int | None = Query(default=None),
    latest: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = get_user_plan(db, user)
    scan = _resolve_scan_for_pdf(db, user, scan_id=scan_id, site_id=site_id, latest=latest)
    _require_finished(scan)
    _enforce_history_policy(db, user, plan, scan)
    return Response(status_code=200, headers={"Content-Type": "application/pdf"})


# ✅ Paid-only: Email report (sends link)
@router.post("/email")
@limiter.limit("5/minute")  # ✅ rate limit per IP
def email_report(
    request: Request,  # ✅ IMPORTANT: required by SlowAPI
    to_email: str = Query(..., description="Recipient email"),
    scan_id: int | None = Query(default=None),
    site_id: int | None = Query(default=None),
    latest: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plan = get_user_plan(db, user)
    if plan.name == "free":
        raise HTTPException(status_code=403, detail="Email reports are available on Paid plan only")

    _enforce_report_quota(db, user, plan, kind="pdf_email")

    scan = _resolve_scan_for_pdf(db, user, scan_id=scan_id, site_id=site_id, latest=latest)
    _require_finished(scan)
    _enforce_history_policy(db, user, plan, scan)

    token = _create_share_link(db, user_id=user.id, scan_id=scan.id, ttl_minutes=15)

    public_base = os.getenv("PUBLIC_BASE_URL")
    if public_base:
        base_url = public_base.rstrip("/")
    else:
        base_url = str(request.base_url).rstrip("/")

    public_url = f"{base_url}/reports/public/{token}.pdf"

    subject = f"Your SaaS Scanner report (scan {scan.id})"
    html = f"""
    <div style="font-family:Arial, sans-serif; line-height:1.5">
      <h2>SaaS Scanner Report</h2>
      <p>Scan ID: <b>{scan.id}</b> — Type: <b>{scan.scan_type}</b> — Status: <b>{scan.status}</b></p>
      <p>This link is valid for <b>15 minutes</b>:</p>
      <p><a href="{public_url}">{public_url}</a></p>
      <p style="color:#666;font-size:12px">If you didn’t request this email, you can ignore it.</p>
    </div>
    """

    try:
        resend_resp = send_email(to_email=to_email, subject=subject, html=html)
    except EmailSendError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _log_report_event(db, user_id=user.id, scan_id=scan.id, kind="pdf_email")
    return {"ok": True, "sent_to": to_email, "scan_id": scan.id, "resend": resend_resp}


# ✅ public PDF by token (no auth)
@router.get("/public/{token}.pdf")
@limiter.limit("20/minute")  # ✅ rate limit per IP
def public_report_pdf(
    token: str,
    request: Request,  # ✅ IMPORTANT: required by SlowAPI
    db: Session = Depends(get_db),
):
    link = db.query(ReportShareLink).filter(ReportShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid token")

    now = datetime.now(timezone.utc)
    exp = _as_utc(link.expires_at)
    if not exp or exp <= now:
        raise HTTPException(status_code=410, detail="Link expired")

    scan = db.query(Scan).filter(Scan.id == link.scan_id, Scan.user_id == link.user_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    site = db.query(Site).filter(Site.id == scan.site_id, Site.user_id == link.user_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    user = db.query(User).filter(User.id == link.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan = get_user_plan(db, user)

    summary = scan.summary or {}
    headers = summary.get("headers") or {}
    sec_headers = headers.get("security_headers") or {}
    tls = summary.get("tls") or {}
    crawl = summary.get("crawl") or {}
    findings = summary.get("findings") or []

    include_pages = bool(plan.allow_history)
    pages: list[ScanPage] = []
    if include_pages:
        pages = (
            db.query(ScanPage)
            .filter(ScanPage.scan_id == scan.id)
            .order_by(ScanPage.id.asc())
            .all()
        )

    pdf = _build_pdf_bytes(
        plan_name=plan.name,
        scan=scan,
        site=site,
        sec_headers=sec_headers,
        tls=tls,
        crawl=crawl,
        findings=findings,
        pages=pages,
        include_pages=include_pages,
    )

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="scan-{scan.id}.pdf"'},
    )


# legacy
@router.get("/scans/{scan_id}.pdf")
def scan_report_pdf_legacy(
    scan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return report_pdf(scan_id=scan_id, site_id=None, latest=True, db=db, user=user)


@router.head("/scans/{scan_id}.pdf")
def scan_report_head_legacy(
    scan_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # ✅ FIX: HEAD should call report_pdf_head
    return report_pdf_head(scan_id=scan_id, site_id=None, latest=True, db=db, user=user)