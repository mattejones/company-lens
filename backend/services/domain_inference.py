from pydantic import BaseModel, Field
from services.llm import build_llm_adapter, LLMAdapter
from utils.prompts import render_prompt


# --- Output schema ---

class DomainCandidate(BaseModel):
    domain: str = Field(description="A plausible domain name including TLD, e.g. monzo.com")
    reasoning: str = Field(description="Why this domain is a plausible match for the company")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)


class DomainInferenceResult(BaseModel):
    candidates: list[DomainCandidate] = Field(
        description="Ranked list of domain candidates, most confident first"
    )


class DomainInferenceService:
    """Infer likely domain names for a given Companies House company profile."""

    def __init__(self):
        self._llm: LLMAdapter = build_llm_adapter()
        self.last_prompts: dict = {}

    async def infer(self, company_data: dict) -> DomainInferenceResult:
        system_prompt = render_prompt("domain_inference_system.j2")
        user_prompt = render_prompt("domain_inference_user.j2", **_extract_context(company_data))

        self.last_prompts = {"system": system_prompt, "user": user_prompt}

        return await self._llm.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=DomainInferenceResult,
        )


def _extract_context(company_data: dict) -> dict:
    """Extract the most signal-rich fields from a CH profile for prompt rendering."""
    address = company_data.get("registered_office_address", {})
    sic_codes = company_data.get("sic_codes", [])
    locality = address.get("locality", "")
    postcode = address.get("postal_code", "")

    return {
        "company_name": company_data.get("company_name", "Unknown"),
        "status": company_data.get("company_status", "unknown"),
        "company_type": company_data.get("type", "unknown"),
        "date_of_creation": company_data.get("date_of_creation", "unknown"),
        "sic_codes": ", ".join(sic_codes) if sic_codes else "not provided",
        "location": ", ".join(filter(None, [locality, postcode])),
    }
