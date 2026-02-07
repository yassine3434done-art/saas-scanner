import httpx
from app.ssrf.guard import validate_url_target

DEFAULT_TIMEOUT = 10.0

def safe_get(url: str, *, timeout: float = DEFAULT_TIMEOUT, headers: dict | None = None) -> httpx.Response:
    # Validate scheme/host + DNS/IP checks (anti-SSRF + anti-rebinding basic)
    validate_url_target(url)

    h = {"User-Agent": "SaaS-Scanner/1.0"}
    if headers:
        h.update(headers)

    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        return client.get(url, headers=h)