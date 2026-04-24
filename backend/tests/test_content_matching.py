import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from utils.content_matching import score_content_match, _clean_company_name


# --- score_content_match ---

def test_score_returns_none_for_no_content():
    assert score_content_match("Monzo Bank", None) is None


def test_score_returns_none_for_empty_content():
    assert score_content_match("Monzo Bank", {}) is None


def test_score_high_for_exact_title_match():
    content = {"title": "Monzo - Online Banking", "meta_description": None, "body_sample": None}
    score = score_content_match("MONZO BANK LIMITED", content)
    assert score is not None
    assert score > 0.7


def test_score_low_for_unrelated_content():
    content = {"title": "Pizza Hut - Order Online", "meta_description": "Order pizza online", "body_sample": None}
    score = score_content_match("MONZO BANK LIMITED", content)
    assert score is not None
    assert score < 0.4


def test_score_handles_word_order_via_token_set_ratio():
    # token_set_ratio should handle reversed/reordered company name tokens
    content = {"title": "Bank Monzo | Home", "meta_description": None, "body_sample": None}
    score = score_content_match("MONZO BANK LIMITED", content)
    assert score is not None
    assert score > 0.6


def test_score_og_description_contributes():
    content = {
        "title": "Home",
        "og_description": "Monzo is a digital bank based in the UK",
        "meta_description": None,
        "body_sample": None,
    }
    score = score_content_match("MONZO BANK LIMITED", content)
    assert score is not None
    assert score > 0.5


def test_clean_company_name_strips_suffixes():
    assert _clean_company_name("MONZO BANK LIMITED") == "monzo bank"
    assert _clean_company_name("ACME GROUP PLC") == "acme"
    assert _clean_company_name("Smith & Jones LLP") == "smith & jones"


# --- HTTP fallback ---

@pytest.mark.asyncio
async def test_fetch_falls_back_to_http():
    """If HTTPS fails, HTTP should be attempted."""
    from utils.content_matching import fetch_content_signals

    call_count = {"n": 0}

    async def mock_fetch(url: str, timeout: float):
        call_count["n"] += 1
        if url.startswith("https"):
            return None  # HTTPS fails
        return {"title": "Fallback via HTTP", "meta_description": None, "body_sample": None, "og_title": None, "og_description": None}

    with patch("utils.content_matching._fetch", side_effect=mock_fetch):
        result = await fetch_content_signals("example.com")

    assert result is not None
    assert result["title"] == "Fallback via HTTP"
    assert call_count["n"] == 2  # tried both schemes


@pytest.mark.asyncio
async def test_fetch_returns_none_if_both_fail():
    from utils.content_matching import fetch_content_signals

    with patch("utils.content_matching._fetch", return_value=None):
        result = await fetch_content_signals("example.com")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_returns_https_result_without_fallback():
    from utils.content_matching import fetch_content_signals

    https_result = {"title": "HTTPS Works", "meta_description": None, "body_sample": None, "og_title": None, "og_description": None}
    call_count = {"n": 0}

    async def mock_fetch(url: str, timeout: float):
        call_count["n"] += 1
        return https_result  # HTTPS succeeds immediately

    with patch("utils.content_matching._fetch", side_effect=mock_fetch):
        result = await fetch_content_signals("example.com")

    assert result == https_result
    assert call_count["n"] == 1  # should not have tried HTTP
