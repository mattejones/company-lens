import pytest
from unittest.mock import AsyncMock, patch
from services.verification import (
    VerificationService,
    VerificationResult,
    VerifiedCandidate,
    _apply_redirect_signals,
    _compute_verification_score,
    _compute_final_score,
)

MOCK_INFERENCE_RESULT = {
    "candidates": [
        {"domain": "monzo.com", "reasoning": "Direct name mapping", "confidence": 0.95},
        {"domain": "monzo.co.uk", "reasoning": "UK TLD variant", "confidence": 0.90},
        {"domain": "monzoapp.com", "reasoning": "App-focused domain", "confidence": 0.70},
    ]
}

# _check_dns now returns (mx, a, nameservers, is_parked)
DNS_OK = (True, True, ["ns1.example.com"], False)
DNS_PARKED = (False, False, ["ns1.afternic.com"], True)
DNS_EMPTY = (False, False, [], False)

# _check_https now returns (is_live, status_code, redirect_url)
HTTPS_OK = (True, 200, None)
HTTPS_REDIRECT = (True, 301, "https://monzo.com")
HTTPS_DEAD = (False, None, None)

# _check_whois now returns (registered, dict)
WHOIS_OK = (True, {"registrar": "Test Registrar", "org": "Monzo Bank Ltd"})
WHOIS_EMPTY = (False, None)


def _make_candidate(domain: str, confidence: float = 0.8, **kwargs) -> VerifiedCandidate:
    defaults = dict(
        reasoning="test",
        mx_record=False,
        a_record=False,
        nameservers=[],
        https_live=False,
        https_status_code=None,
        https_redirect_domain=None,
        whois_registered=False,
        whois_data=None,
        ssl_info=None,
        ssl_org_match=None,
        content_signals=None,
        is_parked=False,
        redirects_to_candidate=None,
        content_match_score=None,
        verification_score=None,
        final_score=None,
    )
    return VerifiedCandidate(domain=domain, confidence=confidence, **{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_verify_returns_all_candidates():
    with patch("services.verification._check_dns", return_value=DNS_OK), \
         patch("services.verification._check_https", new=AsyncMock(return_value=HTTPS_OK)), \
         patch("services.verification._check_whois", return_value=WHOIS_OK), \
         patch("services.verification.extract_ssl_info", return_value=None), \
         patch("services.verification.fetch_content_signals", new=AsyncMock(return_value=None)):

        service = VerificationService(company_name="Monzo Bank Limited")
        result = await service.verify(MOCK_INFERENCE_RESULT)

        assert isinstance(result, VerificationResult)
        assert len(result.candidates) == 3


@pytest.mark.asyncio
async def test_verify_candidates_ranked_by_final_score():
    with patch("services.verification._check_dns", return_value=DNS_OK), \
         patch("services.verification._check_https", new=AsyncMock(return_value=HTTPS_OK)), \
         patch("services.verification._check_whois", return_value=WHOIS_OK), \
         patch("services.verification.extract_ssl_info", return_value=None), \
         patch("services.verification.fetch_content_signals", new=AsyncMock(return_value=None)):

        service = VerificationService(company_name="Monzo Bank Limited")
        result = await service.verify(MOCK_INFERENCE_RESULT)

        scores = [c.final_score for c in result.candidates]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_parked_domain_receives_low_score():
    with patch("services.verification._check_dns", return_value=DNS_PARKED), \
         patch("services.verification._check_https", new=AsyncMock(return_value=HTTPS_DEAD)), \
         patch("services.verification._check_whois", return_value=WHOIS_EMPTY), \
         patch("services.verification.extract_ssl_info", return_value=None), \
         patch("services.verification.fetch_content_signals", new=AsyncMock(return_value=None)):

        service = VerificationService(company_name="Monzo Bank Limited")
        result = await service.verify({"candidates": [
            {"domain": "monzoapp.com", "reasoning": "Parked", "confidence": 0.70}
        ]})

        assert result.candidates[0].is_parked is True
        assert result.candidates[0].verification_score < 0


@pytest.mark.asyncio
async def test_redirect_injection_adds_new_candidate():
    call_count = 0

    async def mock_https(domain):
        nonlocal call_count
        call_count += 1
        if domain == "monzo.co.uk":
            return (True, 301, "https://monzo.com/en-gb")
        return HTTPS_DEAD

    with patch("services.verification._check_dns", return_value=DNS_EMPTY), \
         patch("services.verification._check_https", new=AsyncMock(side_effect=mock_https)), \
         patch("services.verification._check_whois", return_value=WHOIS_EMPTY), \
         patch("services.verification.extract_ssl_info", return_value=None), \
         patch("services.verification.fetch_content_signals", new=AsyncMock(return_value=None)), \
         patch("services.verification.is_safe_redirect", return_value=True), \
         patch("services.verification.extract_redirect_domain", return_value="monzo.com"):

        service = VerificationService(company_name="Monzo Bank Limited")
        result = await service.verify({"candidates": [
            {"domain": "monzo.co.uk", "reasoning": "UK TLD", "confidence": 0.90},
        ]})

        domains = [c.domain for c in result.candidates]
        assert "monzo.com" in domains
        injected = next(c for c in result.candidates if c.domain == "monzo.com")
        assert injected.discovered_via_redirect is True


def test_redirect_to_higher_candidate_boosts_target():
    candidates = [
        _make_candidate("monzo.com", confidence=0.95),
        _make_candidate("monzo.co.uk", confidence=0.90, https_redirect_domain="monzo.com"),
    ]
    _apply_redirect_signals(candidates, {"monzo.com", "monzo.co.uk"})

    monzo_com = next(c for c in candidates if c.domain == "monzo.com")
    assert getattr(monzo_com, "_redirect_boost", 0.0) > 0.0


def test_redirect_to_lower_candidate_no_boost():
    candidates = [
        _make_candidate("monzo.co.uk", confidence=0.90, https_redirect_domain="monzo.com"),
        _make_candidate("monzo.com", confidence=0.95),
    ]
    _apply_redirect_signals(candidates, {"monzo.com", "monzo.co.uk"})

    monzo_com = next(c for c in candidates if c.domain == "monzo.com")
    assert getattr(monzo_com, "_redirect_boost", 0.0) == 0.0


def test_final_score_bounded_zero_to_one():
    candidate = _make_candidate("monzo.com", confidence=0.95, mx_record=True, a_record=True)
    candidate.verification_score = _compute_verification_score(candidate)
    candidate.final_score = _compute_final_score(candidate)

    assert 0.0 <= candidate.final_score <= 1.0


def test_mx_record_contributes_positively():
    with_mx = _make_candidate("monzo.com", mx_record=True)
    without_mx = _make_candidate("monzo.com", mx_record=False)

    with_mx.verification_score = _compute_verification_score(with_mx)
    without_mx.verification_score = _compute_verification_score(without_mx)

    assert with_mx.verification_score > without_mx.verification_score
