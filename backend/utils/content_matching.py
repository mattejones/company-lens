import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import re


async def fetch_content_signals(domain: str, timeout: float = 10.0) -> dict | None:
    """Fetch a domain's homepage and extract signals for fuzzy matching.

    Attempts HTTPS first, falls back to HTTP if HTTPS fails.
    Returns title, OG tags, meta description, and a sample of visible body text.
    Returns None if the page is unreachable or not HTML.
    """
    for scheme in ("https", "http"):
        result = await _fetch(f"{scheme}://{domain}", timeout)
        if result is not None:
            return result
    return None


async def _fetch(url: str, timeout: float) -> dict | None:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            verify=False,
            max_redirects=2,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CompanyLens/1.0)"},
        ) as client:
            response = await client.get(url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                return None
            if response.status_code >= 400:
                return None
            html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Standard title
        title = soup.title.string.strip() if soup.title and soup.title.string else None

        # OG title — often cleaner than <title> which may include site suffix
        og_title = _get_meta(soup, property="og:title")
        og_description = _get_meta(soup, property="og:description")

        # Meta description
        meta_desc = _get_meta(soup, name="description")

        # Prefer OG title over standard title if present
        effective_title = og_title or title

        body_text = _extract_body_text(soup)

        return {
            "title": effective_title,
            "og_title": og_title,
            "og_description": og_description,
            "meta_description": meta_desc,
            "body_sample": body_text[:500] if body_text else None,
        }

    except Exception:
        return None


def score_content_match(company_name: str, content: dict | None) -> float | None:
    """Score how well page content matches a company name using fuzzy matching.

    Uses a weighted combination of signals. Each signal is scored using both
    partial_ratio (substring match) and token_set_ratio (word-order agnostic),
    taking the higher of the two — this handles cases like trading name
    abbreviations or reversed word order in page titles.

    Returns None if no content was retrieved.
    """
    if not content:
        return None

    clean_name = _clean_company_name(company_name)
    scores = []

    def best_score(text: str) -> float:
        t = text.lower()
        return max(
            fuzz.partial_ratio(clean_name, t),
            fuzz.token_set_ratio(clean_name, t),
        )

    if content.get("title"):
        scores.append((best_score(content["title"]), 0.40))

    if content.get("og_description"):
        scores.append((best_score(content["og_description"]), 0.25))

    if content.get("meta_description"):
        scores.append((best_score(content["meta_description"]), 0.20))

    if content.get("body_sample"):
        scores.append((best_score(content["body_sample"]), 0.15))

    if not scores:
        return None

    weighted = sum(score * weight for score, weight in scores)
    total_weight = sum(weight for _, weight in scores)
    return round((weighted / total_weight) / 100.0, 4)


def _get_meta(soup: BeautifulSoup, **attrs) -> str | None:
    """Extract content from a meta tag by arbitrary attributes."""
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _clean_company_name(name: str) -> str:
    """Strip common company suffixes and normalise for fuzzy comparison."""
    suffixes = r"\b(limited|ltd|plc|llp|group|holdings|international|uk|gb)\b"
    cleaned = re.sub(suffixes, "", name.lower(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_body_text(soup: BeautifulSoup) -> str:
    """Extract a clean sample of visible body text, ignoring scripts and styles."""
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()
