import json
from pydantic import BaseModel, Field
from services.llm import build_llm_adapter, LLMAdapter
from utils.prompts import render_prompt
from services.domain_inference import _extract_context


class RankedCandidate(BaseModel):
    domain: str = Field(description="The domain name")
    reasoning: str = Field(description="Updated reasoning based on all available evidence")
    confidence: float = Field(description="Revised confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    is_squatted_or_parked: bool = Field(description="Whether the domain appears squatted, parked, or third-party owned")
    is_primary_candidate: bool = Field(description="Whether this is the most likely primary domain for the company")


class DomainRankingResult(BaseModel):
    candidates: list[RankedCandidate] = Field(
        description="All candidates re-ranked by likelihood of being the company's primary domain"
    )
    summary: str = Field(description="Brief summary of ranking rationale and key signals used")


class DomainRankingService:
    """Stage 2 LLM — re-ranks verified domain candidates using structured evidence."""

    def __init__(self):
        self._llm: LLMAdapter = build_llm_adapter()

    async def rank(self, company_data: dict, verification_result: dict) -> DomainRankingResult:
        context = _extract_context(company_data)

        candidates_for_prompt = [
            _summarise_candidate(c)
            for c in verification_result.get("candidates", [])
        ]

        system_prompt = render_prompt("domain_ranking_system.j2")
        user_prompt = render_prompt(
            "domain_ranking_user.j2",
            candidates_json=json.dumps(candidates_for_prompt, indent=2),
            **context,
        )

        return await self._llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=DomainRankingResult,
        )


def _summarise_candidate(c: dict) -> dict:
    whois = c.get("whois_data") or {}
    ssl = c.get("ssl_info") or {}
    content = c.get("content_signals") or {}

    return {
        "domain": c.get("domain"),
        "dns": {
            "mx_record": c.get("mx_record"),
            "a_record": c.get("a_record"),
            "nameservers": c.get("nameservers", []),
            "is_parked": c.get("is_parked"),
        },
        "https": {
            "live": c.get("https_live"),
            "status_code": c.get("https_status_code"),
            "redirect_domain": c.get("https_redirect_domain"),
            "redirects_to_candidate": c.get("redirects_to_candidate"),
        },
        "ssl": {
            "org": ssl.get("org"),
            "common_name": ssl.get("common_name"),
            "sans": ssl.get("sans", []),
            "issuer": ssl.get("issuer"),
        },
        "whois": {
            "registered": c.get("whois_registered"),
            "registrar": whois.get("registrar"),
            "org": whois.get("org"),
            "registrant_name": whois.get("name"),
            "country": whois.get("country"),
            "creation_date": whois.get("creation_date"),
            "expiration_date": whois.get("expiration_date"),
        },
        "content": {
            "title": content.get("title"),
            "meta_description": content.get("meta_description"),
            "content_match_score": c.get("content_match_score"),
        },
        "scores": {
            "llm_confidence": c.get("confidence"),
            "verification_score": c.get("verification_score"),
            "final_score": c.get("final_score"),
            "discovered_via_redirect": c.get("discovered_via_redirect", False),
        },
    }
