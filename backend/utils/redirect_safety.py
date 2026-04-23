import re
from urllib.parse import urlparse

# TLDs considered high-risk when a redirect crosses into them from a legitimate domain
SUSPICIOUS_TLDS = {".ru", ".cn", ".tk", ".ml", ".ga", ".cf", ".gq", ".pw", ".top", ".xyz"}

# Known parking/malicious nameserver fragments already handled in verification,
# but also block redirects to these domains directly
BLOCKED_REDIRECT_DOMAINS = {
    "afternic.com", "sedo.com", "dan.com", "parkingcrew.net",
    "godaddy.com", "hugedomains.com", "uniregistry.com",
    "bodis.com", "above.com",
}


def is_safe_redirect(original_domain: str, redirect_url: str) -> bool:
    """Validate that a redirect target is safe to inject as a candidate.

    Rejects:
    - Bare IP addresses
    - Non-standard ports
    - Known parking/marketplace domains
    - Suspicious TLD hops (e.g. .co.uk → .ru)
    - Non HTTP/HTTPS schemes
    - Overly deep subdomains (likely CDN or tracking)
    """
    try:
        parsed = urlparse(redirect_url if "://" in redirect_url else f"https://{redirect_url}")

        if parsed.scheme not in ("http", "https"):
            return False

        host = parsed.hostname or ""

        if not host:
            return False

        if parsed.port and parsed.port not in (80, 443):
            return False

        if _is_ip_address(host):
            return False

        if any(blocked in host for blocked in BLOCKED_REDIRECT_DOMAINS):
            return False

        original_tld = _extract_tld(original_domain)
        redirect_tld = _extract_tld(host)
        if original_tld and redirect_tld:
            if redirect_tld in SUSPICIOUS_TLDS and original_tld not in SUSPICIOUS_TLDS:
                return False

        subdomain_parts = host.split(".")
        if len(subdomain_parts) > 4:
            return False

        return True

    except Exception:
        return False


def extract_redirect_domain(redirect_url: str) -> str | None:
    """Extract a clean domain from a redirect URL, stripping www prefix."""
    try:
        parsed = urlparse(redirect_url if "://" in redirect_url else f"https://{redirect_url}")
        host = parsed.hostname or ""
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


def _is_ip_address(host: str) -> bool:
    ipv4 = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    return bool(ipv4.match(host))


def _extract_tld(domain: str) -> str | None:
    parts = domain.rstrip(".").split(".")
    return f".{parts[-1]}" if parts else None
