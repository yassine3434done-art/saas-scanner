import ssl
import socket
import time
from urllib.parse import urlparse, urljoin
from collections import deque

from app.ssrf.http import safe_get
from app.ssrf.guard import validate_url_target

def fetch_tls_info(url: str) -> dict:
    p = urlparse(url)
    host = p.hostname
    port = p.port or (443 if p.scheme == "https" else 80)

    if p.scheme != "https":
        return {"enabled": False}

    # SSRF validation (host resolution)
    validate_url_target(url)

    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=8) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            proto = ssock.version()
            cipher = ssock.cipher()
            return {
                "enabled": True,
                "protocol": proto,
                "cipher": cipher[0] if cipher else None,
                "subject": cert.get("subject"),
                "issuer": cert.get("issuer"),
                "notBefore": cert.get("notBefore"),
                "notAfter": cert.get("notAfter"),
            }

def public_headers_check(resp) -> dict:
    h = {k.lower(): v for k, v in resp.headers.items()}
    return {
        "status_code": resp.status_code,
        "security_headers": {
            "strict-transport-security": h.get("strict-transport-security"),
            "content-security-policy": h.get("content-security-policy"),
            "x-frame-options": h.get("x-frame-options"),
            "x-content-type-options": h.get("x-content-type-options"),
            "referrer-policy": h.get("referrer-policy"),
            "permissions-policy": h.get("permissions-policy"),
        }
    }

def extract_links_same_origin(base_url: str, html: str) -> list[str]:
    # very simple extraction to keep MVP small (no bs4)
    # finds href="..."
    links: list[str] = []
    base = urlparse(base_url)
    token = 'href="'
    i = 0
    while True:
        j = html.find(token, i)
        if j == -1:
            break
        j += len(token)
        k = html.find('"', j)
        if k == -1:
            break
        href = html[j:k].strip()
        i = k + 1

        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue

        abs_url = urljoin(base_url, href)
        p = urlparse(abs_url)
        if p.scheme not in ("http", "https") or not p.hostname:
            continue
        if p.hostname.lower().strip(".") == base.hostname.lower().strip("."):
            links.append(abs_url)
    # dedupe
    out = []
    seen = set()
    for u in links:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

def crawl_light(start_url: str, *, max_pages: int, max_seconds: int) -> dict:
    start = time.time()
    q = deque([start_url])
    seen = set([start_url])
    pages: list[dict] = []

    while q:
        if len(pages) >= max_pages:
            break
        if time.time() - start > max_seconds:
            break

        url = q.popleft()
        try:
            r = safe_get(url, timeout=8)
            pages.append({"url": url, "status_code": r.status_code})
            ctype = (r.headers.get("content-type") or "").lower()
            if "text/html" in ctype and r.text:
                for link in extract_links_same_origin(start_url, r.text):
                    if link not in seen and len(seen) < (max_pages * 5):  # small cap against explosion
                        seen.add(link)
                        q.append(link)
        except Exception:
            pages.append({"url": url, "status_code": None})

    return {
        "pages": pages,
        "metrics": {
            "visited": len(pages),
            "unique_seen": len(seen),
            "time_spent_sec": int(time.time() - start),
        }
    }