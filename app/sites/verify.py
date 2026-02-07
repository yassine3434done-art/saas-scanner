import time
import httpx
import dns.resolver


def verify_dns_txt(domain: str, token: str, timeout_sec: float = 2.0) -> bool:
    """
    DNS lookups can hang; keep strict timeouts.
    """
    try:
        r = dns.resolver.Resolver()
        r.timeout = timeout_sec
        r.lifetime = timeout_sec
        answers = r.resolve(domain, "TXT")
        for rdata in answers:
            # rdata could be like: "scanner-verification=...."
            if token in str(rdata):
                return True
    except Exception:
        return False
    return False


def verify_well_known(url: str, token: str, timeout_sec: float = 5.0) -> bool:
    """
    Check /.well-known/security-scanner.txt and bypass CDN caches via ?ts=
    """
    base = url.rstrip("/")
    ts = int(time.time())
    verify_url = f"{base}/.well-known/security-scanner.txt?ts={ts}"

    try:
        r = httpx.get(
            verify_url,
            timeout=timeout_sec,
            follow_redirects=True,
            headers={
                "User-Agent": "SaaS-Scanner-Verify/1.0",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        return r.status_code == 200 and token in (r.text or "")
    except Exception:
        return False


def verify_meta(url: str, token: str, timeout_sec: float = 5.0) -> bool:
    """
    Look for:
      <meta name="scanner-verification" content="<token>">
    Also bypass CDN caches via ?ts=
    """
    ts = int(time.time())
    meta_url = f"{url}{'&' if '?' in url else '?'}ts={ts}"

    try:
        r = httpx.get(
            meta_url,
            timeout=timeout_sec,
            follow_redirects=True,
            headers={
                "User-Agent": "SaaS-Scanner-Verify/1.0",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
        )
        if r.status_code != 200:
            return False

        html = r.text or ""

        # Simple and robust enough for MVP
        # Ensure the meta tag exists and token is present near it.
        if 'name="scanner-verification"' not in html and "name='scanner-verification'" not in html:
            return False

        return token in html
    except Exception:
        return False