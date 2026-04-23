import asyncio
import json
import httpx
import whois
import dns.resolver
from pydantic import BaseModel, Field
from utils.redirect_safety import is_safe_redirect, extract_redirect_domain
from utils.ssl_info import extract_ssl_info
from utils.content_matching import fetch_content_signals, score_content_match

# --- Parking provider nameservers ---

PARKED_NAMESERVERS = {
    "afternic.com", "sedo.com", "dan.com", "parkingcrew.net",
    "bodis.com", "domainsponsor.com", "above.com", "parklogic.com",
    "hugedomains.com", "uniregistry.com", "undeveloped.com", "efty.com",
}

# --- Scoring weights ---

MX_WEIGHT = 0.30
A_RECORD_WEIGHT = 0.10
HTTPS_LIVE_WEIGHT = 0.15
SSL_ORG_MATCH_WEIGHT = 0.15
CONTENT_MATCH_WEIGHT = 0.15
REDIRECT_TO_CANDIDATE_PENALTY = -0.25
REDIRECT_CANONICAL_BOOST = 0.10
REDIRECT_UNKNOWN_PENALTY = -0.35
PARKED_PENALTY = -0.50

LLM_CONFIDENCE_WEIGHT = 0.40
VERIFICATION_WEIGHT = 0.60


# --- Models ---

class SSLInfo(BaseModel):
    org: str | None = None
    common_name: str | None = None
    sans: list[str] = Field(default_factory=list)
    issuer: str | None = None
    not_after: str | None = None


class ContentSignals(BaseModel):
    title: str | None = None
    meta_description: str | None = None
    body_sample: str | None = None


class VerifiedCandidate(BaseModel):
    domain: str
    reasoning: str
    confidence: float

    # DNS
    mx_record: bool | None = Field(None, description="Domain has MX records")
    a_record: bool | None = Field(None, description="Domain resolves via A record")
    nameservers: list[str] = Field(default_factory=list, description="Resolved nameservers")
    is_parked: bool | None = Field(None, description="Domain appears parked based on nameservers")

    # HTTPS
    https_live: bool | None = Field(None, description="Domain responds to HTTPS")
    https_status_code: int | None = Field(None, description="HTTP response status code")
    https_redirect_domain: str | None = Field(None, description="Final domain after redirects, if different")
    redirects_to_candidate: str | None = Field(None, description="Redirect target if it is another candidate")

    # SSL
    ssl_info: SSLInfo | None = Field(None, description="SSL certificate signals")
    ssl_org_match: bool | None = Field(None, description="SSL org field matches company name")

    # WHOIS
    whois_registered: bool | None = Field(None, description="Domain appears registered")
    whois_data: dict | None = Field(None, description="Structured WHOIS data")

    # Content
    content_signals: ContentSignals | None = Field(None, description="Fetched page content signals")
    content_match_score: float | None = Field(None, description="Fuzzy match score against company name")

    # Pipeline provenance
    discovered_via_redirect: bool = Field(False, description="Candidate injected from a redirect target")

    # Scores
    verification_score: float | None = None
    final_score: float | None = None


class VerificationResult(BaseModel):
    candidates: list[VerifiedCandidate] = Field(
        description="Domain candidates enriched with all verification signals, ranked by final_score"
    )


# --- Service ---

class VerificationService:
    def __init__(self, company_name: str = ""):
        self.company_name = company_name

    async def verify(self, inference_result: dict, company_name: str = "") -> VerificationResult:
        self.company_name = company_name or self.company_name
        candidates = inference_result.get("candidates", [])
        max_injected = len(candidates) * 2

        # Pass 1 — individual checks in parallel
        verified = list(await asyncio.gather(*[
            self._check_candidate(c) for c in candidates
        ]))

        # Pass 2 — redirect injection
        injected = await self._inject_redirect_candidates(verified, max_injected)
        verified.extend(injected)

        domain_set = {c.domain for c in verified}

        # Pass 3 — cross-candidate redirect signals
        _apply_redirect_signals(verified, domain_set)

        # Pass 4 — score and re-rank
        for candidate in verified:
            candidate.verification_score = _compute_verification_score(candidate)
            candidate.final_score = _compute_final_score(candidate)

        verified.sort(key=lambda c: c.final_score or 0.0, reverse=True)
        return VerificationResult(candidates=verified)

    async def _check_candidate(self, candidate: dict | VerifiedCandidate) -> VerifiedCandidate:
        if isinstance(candidate, VerifiedCandidate):
            domain = candidate.domain
            base = {"domain": domain, "reasoning": candidate.reasoning, "confidence": candidate.confidence}
        else:
            domain = candidate["domain"]
            base = {
                "domain": domain,
                "reasoning": candidate.get("reasoning", ""),
                "confidence": candidate.get("confidence", 0.0),
            }

        mx, a, nameservers, is_parked = await asyncio.to_thread(_check_dns, domain)
        https_live, status_code, redirect_url = await _check_https(domain)
        redirect_domain = extract_redirect_domain(redirect_url) if redirect_url else None
        ssl_info = await asyncio.to_thread(extract_ssl_info, domain)
        whois_registered, whois_data = await asyncio.to_thread(_check_whois, domain)
        content = await fetch_content_signals(domain)
        content_score = score_content_match(self.company_name, content) if self.company_name else None
        ssl_org_match = _check_ssl_org_match(ssl_info, self.company_name) if ssl_info else None

        return VerifiedCandidate(
            **base,
            mx_record=mx,
            a_record=a,
            nameservers=nameservers,
            is_parked=is_parked,
            https_live=https_live,
            https_status_code=status_code,
            https_redirect_domain=redirect_domain,
            ssl_info=SSLInfo(**ssl_info) if ssl_info else None,
            ssl_org_match=ssl_org_match,
            whois_registered=whois_registered,
            whois_data=whois_data,
            content_signals=ContentSignals(**content) if content else None,
            content_match_score=content_score,
        )

    async def _inject_redirect_candidates(
        self,
        verified: list[VerifiedCandidate],
        max_injected: int,
    ) -> list[VerifiedCandidate]:
        existing_domains = {c.domain for c in verified}
        seen_redirects: set[str] = set()
        to_inject: list[str] = []

        for candidate in verified:
            redirect = candidate.https_redirect_domain
            if not redirect:
                continue
            if redirect in existing_domains or redirect in seen_redirects:
                continue
            if not is_safe_redirect(candidate.domain, redirect):
                continue
            seen_redirects.add(redirect)
            to_inject.append(redirect)
            if len(to_inject) >= max_injected:
                break

        if not to_inject:
            return []

        injected = list(await asyncio.gather(*[
            self._check_candidate({
                "domain": domain,
                "reasoning": "Discovered via redirect from a candidate domain",
                "confidence": 0.0,
            })
            for domain in to_inject
        ]))

        for candidate in injected:
            candidate.discovered_via_redirect = True

        return injected


# --- DNS ---

def _check_dns(domain: str) -> tuple[bool, bool, list[str], bool]:
    """Return (mx_present, a_present, nameservers, is_parked)."""
    mx = False
    a = False
    nameservers = []
    is_parked = False

    try:
        ns_answers = dns.resolver.resolve(domain, "NS")
        nameservers = [str(ns).lower().rstrip(".") for ns in ns_answers]
        is_parked = any(
            any(provider in ns for provider in PARKED_NAMESERVERS)
            for ns in nameservers
        )
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        pass

    try:
        mx = len(dns.resolver.resolve(domain, "MX")) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        pass

    try:
        a = len(dns.resolver.resolve(domain, "A")) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        pass

    return mx, a, nameservers, is_parked


# --- HTTPS ---

async def _check_https(domain: str) -> tuple[bool, int | None, str | None]:
    """Returns (is_live, status_code, final_url_if_redirected)."""
    url = f"https://{domain}"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=10.0,
            verify=False,
            max_redirects=2,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CompanyLens/1.0)"},
        ) as client:
            response = await client.get(url)
            status = response.status_code
            if status >= 400:
                return False, status, None
            final_url = str(response.url)
            final_host = httpx.URL(final_url).host.lstrip("www.")
            redirect_url = final_url if final_host != domain else None
            return True, status, redirect_url
    except Exception:
        return False, None, None


# --- WHOIS ---

def _check_whois(domain: str) -> tuple[bool, dict | None]:
    """Parse WHOIS into a structured dict rather than raw string."""
    try:
        w = whois.whois(domain)
        if not w.domain_name:
            return False, None

        def _serialise(v):
            if hasattr(v, "isoformat"):
                return v.isoformat()
            if isinstance(v, list):
                return [_serialise(i) for i in v]
            return v

        data = {k: _serialise(v) for k, v in w.items() if v is not None}
        return True, data
    except Exception:
        return False, None


# --- SSL org match ---

def _check_ssl_org_match(ssl_info: dict, company_name: str) -> bool:
    """Loosely check if the SSL org matches the company name."""
    if not ssl_info or not company_name:
        return False
    org = (ssl_info.get("org") or "").lower()
    name = company_name.lower()
    tokens = [t for t in name.split() if len(t) > 3]
    return any(token in org for token in tokens)


# --- Cross-candidate redirect signals ---

def _apply_redirect_signals(candidates: list[VerifiedCandidate], domain_set: set[str]) -> None:
    domain_index = {c.domain: i for i, c in enumerate(candidates)}

    for candidate in candidates:
        redirect = candidate.https_redirect_domain
        if redirect and redirect in domain_set:
            candidate.redirects_to_candidate = redirect
            target_rank = domain_index.get(redirect)
            source_rank = domain_index.get(candidate.domain)
            if target_rank is not None and source_rank is not None and target_rank < source_rank:
                target = next(c for c in candidates if c.domain == redirect)
                current = getattr(target, "_redirect_boost", 0.0)
                object.__setattr__(target, "_redirect_boost", current + REDIRECT_CANONICAL_BOOST)


# --- Scoring ---

def _compute_verification_score(candidate: VerifiedCandidate) -> float:
    score = 0.0

    if candidate.is_parked:
        return max(score + PARKED_PENALTY, -1.0)

    if candidate.mx_record:
        score += MX_WEIGHT
    if candidate.a_record:
        score += A_RECORD_WEIGHT
    if candidate.ssl_org_match:
        score += SSL_ORG_MATCH_WEIGHT

    if candidate.https_live:
        if candidate.https_redirect_domain is None:
            score += HTTPS_LIVE_WEIGHT
        elif candidate.redirects_to_candidate:
            score += REDIRECT_TO_CANDIDATE_PENALTY
        else:
            score += REDIRECT_UNKNOWN_PENALTY
    elif candidate.https_redirect_domain:
        score += REDIRECT_UNKNOWN_PENALTY

    if candidate.content_match_score is not None:
        score += candidate.content_match_score * CONTENT_MATCH_WEIGHT

    score += getattr(candidate, "_redirect_boost", 0.0)
    return round(max(min(score, 1.0), -1.0), 4)


def _compute_final_score(candidate: VerifiedCandidate) -> float:
    normalised = (candidate.verification_score + 1.0) / 2.0

    if candidate.discovered_via_redirect:
        return round(normalised, 4)

    final = (candidate.confidence * LLM_CONFIDENCE_WEIGHT) + (normalised * VERIFICATION_WEIGHT)
    return round(max(min(final, 1.0), 0.0), 4)
