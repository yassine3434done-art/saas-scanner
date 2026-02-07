from urllib.parse import urlparse

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

def extract_domain(url: str) -> str:
    p = urlparse(url)
    host = p.hostname or ""
    return host.lower()