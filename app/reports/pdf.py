from __future__ import annotations

from io import BytesIO
from datetime import timezone
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _as_utc(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _fmt_dt(dt) -> str:
    dt = _as_utc(dt)
    if not dt:
        return "-"
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _safe(obj, default=None):
    return obj if obj is not None else default


def _draw_kv(c: canvas.Canvas, x: float, y: float, label: str, value: str, max_width: float) -> float:
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, f"{label}:")
    c.setFont("Helvetica", 10)

    text = value or "-"
    # very simple wrap
    words = text.split()
    line = ""
    lines = []
    for w in words:
        t = (line + " " + w).strip()
        if c.stringWidth(t, "Helvetica", 10) <= max_width:
            line = t
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)

    yy = y
    for ln in (lines or ["-"]):
        c.drawString(x + 90, yy, ln)
        yy -= 14
    return yy


def build_scan_pdf(
    *,
    scan: Any,
    site: Any,
    plan_name: str,
    pages: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    """
    scan: Scan model (id/status/type/timestamps/summary/error)
    site: Site model (url/domain/is_verified/verified_at)
    pages: list of {url,status_code,created_at}
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    margin = 2 * cm
    x = margin
    y = H - margin

    def new_page():
        nonlocal y
        c.showPage()
        y = H - margin

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, y, "SaaS Scanner Report")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(x, y, f"Plan: {plan_name}")
    y -= 18

    # Basics
    y = _draw_kv(c, x, y, "Scan ID", str(scan.id), W - 2 * margin)
    y = _draw_kv(c, x, y, "Scan Type", str(scan.scan_type), W - 2 * margin)
    y = _draw_kv(c, x, y, "Status", str(scan.status), W - 2 * margin)
    y = _draw_kv(c, x, y, "Created At", _fmt_dt(scan.created_at), W - 2 * margin)
    y = _draw_kv(c, x, y, "Started At", _fmt_dt(scan.started_at), W - 2 * margin)
    y = _draw_kv(c, x, y, "Finished At", _fmt_dt(scan.finished_at), W - 2 * margin)
    y -= 6

    # Site
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Site")
    y -= 16

    y = _draw_kv(c, x, y, "URL", str(site.url), W - 2 * margin)
    y = _draw_kv(c, x, y, "Domain", str(site.domain), W - 2 * margin)
    y = _draw_kv(c, x, y, "Verified", str(bool(site.is_verified)), W - 2 * margin)
    y = _draw_kv(c, x, y, "Verified At", _fmt_dt(site.verified_at), W - 2 * margin)
    y -= 10

    summary = _safe(scan.summary, {}) or {}

    # Headers
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Headers")
    y -= 16

    headers = (summary.get("headers") or {})
    sec = (headers.get("security_headers") or {})
    y = _draw_kv(c, x, y, "HTTP", str(headers.get("status_code")), W - 2 * margin)
    for k in [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
        "referrer-policy",
        "permissions-policy",
    ]:
        y = _draw_kv(c, x, y, k, str(sec.get(k) or "null"), W - 2 * margin)

    if y < 120:
        new_page()

    # TLS
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "TLS")
    y -= 16

    tls = (summary.get("tls") or {})
    y = _draw_kv(c, x, y, "Enabled", str(tls.get("enabled")), W - 2 * margin)
    if tls.get("enabled"):
        y = _draw_kv(c, x, y, "Protocol", str(tls.get("protocol")), W - 2 * margin)
        y = _draw_kv(c, x, y, "Cipher", str(tls.get("cipher")), W - 2 * margin)
        y = _draw_kv(c, x, y, "NotBefore", str(tls.get("notBefore")), W - 2 * margin)
        y = _draw_kv(c, x, y, "NotAfter", str(tls.get("notAfter")), W - 2 * margin)

    if y < 120:
        new_page()

    # Crawl
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Crawl Metrics")
    y -= 16

    crawl = (summary.get("crawl") or {})
    y = _draw_kv(c, x, y, "Visited", str(crawl.get("visited")), W - 2 * margin)
    y = _draw_kv(c, x, y, "Unique Seen", str(crawl.get("unique_seen")), W - 2 * margin)
    y = _draw_kv(c, x, y, "Time (sec)", str(crawl.get("time_spent_sec")), W - 2 * margin)

    # Findings (advanced)
    findings = summary.get("findings") or []
    if findings:
        if y < 160:
            new_page()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Findings")
        y -= 16

        c.setFont("Helvetica", 10)
        for f in findings:
            line = f"- [{f.get('severity')}] {f.get('title')} ({f.get('id')})"
            c.drawString(x, y, line)
            y -= 14
            ev = str(f.get("evidence") or "")
            if ev:
                c.drawString(x + 14, y, ev[:120])
                y -= 14
            if y < 80:
                new_page()
                c.setFont("Helvetica", 10)

    # Pages appendix (اختياري)
    if pages:
        new_page()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Pages")
        y -= 16

        c.setFont("Helvetica", 9)
        for p in pages:
            url = str(p.get("url") or "")
            sc = str(p.get("status_code") or "")
            dt = str(p.get("created_at") or "")
            line = f"{sc:>3}  {dt}  {url}"
            # truncate
            if len(line) > 140:
                line = line[:137] + "..."
            c.drawString(x, y, line)
            y -= 12
            if y < 60:
                new_page()
                c.setFont("Helvetica", 9)

    # Error if failed
    if scan.status == "failed" and scan.error:
        new_page()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x, y, "Error")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(x, y, str(scan.error)[:4000])

    c.save()
    return buf.getvalue()