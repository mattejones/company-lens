import ssl
import socket
import json


def extract_ssl_info(domain: str, timeout: float = 5.0) -> dict | None:
    """Extract useful signals from a domain's SSL certificate.

    Returns:
        - org: Organisation field from the certificate Subject
        - common_name: CN from the certificate Subject
        - sans: Subject Alternative Names — other domains on the same cert
        - issuer: Certificate issuer (CA name)
        - not_after: Expiry date string

    SANs are particularly valuable — they often reveal other domains
    owned by the same entity, including trading name variants.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))

        sans = []
        for san_type, san_value in cert.get("subjectAltName", []):
            if san_type == "DNS":
                clean = san_value.lstrip("*.")
                if clean and clean != domain:
                    sans.append(clean)

        return {
            "org": subject.get("organizationName"),
            "common_name": subject.get("commonName"),
            "sans": sans,
            "issuer": issuer.get("organizationName"),
            "not_after": cert.get("notAfter"),
        }

    except Exception:
        return None
