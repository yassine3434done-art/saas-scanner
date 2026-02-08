import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {"localhost"}

BLOCKED_IPS = {
    "0.0.0.0",
    "127.0.0.1",
    "169.254.169.254",  # cloud metadata (common)
    "::1",
}

BLOCKED_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (includes metadata range)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),   # CGNAT
    ipaddress.ip_network("224.0.0.0/4"),     # multicast
]

def is_ip_blocked(ip: str) -> bool:
    if ip in BLOCKED_IPS:
        return True
    try:
        addr = ipaddress.ip_address(ip)
        if addr.version == 6:
            if addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_private:
                return True
        for net in BLOCKED_NETS:
            if addr.version == 4 and addr in net:
                return True
        return False
    except ValueError:
        return True

def resolve_all_ips(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None)
    ips: list[str] = []
    for _family, _type, _proto, _canon, sockaddr in infos:
        ip = sockaddr[0]
        if ip not in ips:
            ips.append(ip)
    return ips

def validate_url_target(url: str) -> tuple[str, str]:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError("Only http/https allowed")
    host = p.hostname
    if not host:
        raise ValueError("Invalid host")
    host_l = host.lower().strip(".")
    if host_l in BLOCKED_HOSTNAMES:
        raise ValueError("Blocked hostname")

    ips = resolve_all_ips(host_l)
    if not ips:
        raise ValueError("Cannot resolve host")
    for ip in ips:
        if is_ip_blocked(ip):
            raise ValueError(f"Blocked resolved IP: {ip}")

    return p.scheme, host_l