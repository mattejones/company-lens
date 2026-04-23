from pydantic import BaseModel, Field


class VerifiedCandidate(BaseModel):
    domain: str
    reasoning: str
    confidence: float
    dns_resolved: bool | None = None
    whois_registered: bool | None = None
    http_live: bool | None = None
    content_match_score: float | None = None


class VerificationResult(BaseModel):
    candidates: list[VerifiedCandidate] = Field(
        description="Domain candidates enriched with verification signals"
    )


class VerificationService:
    """Verify domain candidates via DNS, WHOIS, HTTP, and content scraping.

    Each check enriches the candidate with a signal that contributes
    to the final ranking. Stub implementation — checks are not yet performed.
    """

    async def verify(self, inference_result: dict) -> VerificationResult:
        candidates = [
            VerifiedCandidate(**candidate)
            for candidate in inference_result.get("candidates", [])
        ]
        return VerificationResult(candidates=candidates)
