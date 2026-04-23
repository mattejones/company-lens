import httpx
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import re


async def fetch_content_signals(domain: str, timeout: float = 10.0) -> dict | None:
    """Fetch a domain's homepage and extract signals for fuzzy matching.

    Returns title, meta description, and a sample of visible body text.
    Returns None if the page is unreachable or not HTML.
    """
    url = f"https://{domain}"
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

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else None

        meta_desc = None
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        body_text = _extract_body_text(soup)

        return {
            "title": title,
            "meta_description": meta_desc,
            "body_sample": body_text[:500] if body_text else None,
        }

    except Exception:
        return None


def score_content_match(company_name: str, content: dict | None) -> float | None:
    """Score how well page content matches a company name using fuzzy matching.

    Uses a weighted combination of title, meta description, and body text scores.
    Returns None if no content was retrieved.
    """
    if not content:
        return None

    clean_name = _clean_company_name(company_name)
    scores = []

    if content.get("title"):
        scores.append((fuzz.partial_ratio(clean_name, content["title"].lower()), 0.50))

    if content.get("meta_description"):
        scores.append((fuzz.partial_ratio(clean_name, content["meta_description"].lower()), 0.30))

    if content.get("body_sample"):
        scores.append((fuzz.partial_ratio(clean_name, content["body_sample"].lower()), 0.20))

    if not scores:
        return None

    weighted = sum(score * weight for score, weight in scores)
    total_weight = sum(weight for _, weight in scores)
    return round((weighted / total_weight) / 100.0, 4)


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
