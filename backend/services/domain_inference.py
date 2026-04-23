import instructor
import openai
from pydantic import BaseModel, Field
from api.config import settings


# --- Output schema ---

class DomainCandidate(BaseModel):
    domain: str = Field(description="A plausible domain name including TLD, e.g. monzo.com")
    reasoning: str = Field(description="Why this domain is a plausible match for the company")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)


class DomainInferenceResult(BaseModel):
    candidates: list[DomainCandidate] = Field(
        description="Ranked list of domain candidates, most confident first"
    )


# --- Client factory ---

def _build_client() -> instructor.Instructor:
    """Build an instructor-wrapped client from config.

    Both OpenAI and Ollama use the same OpenAI-compatible client —
    switching provider is purely a config change.
    """
    openai_client = openai.AsyncOpenAI(
        api_key=settings.openai_api_key if settings.llm_provider == "openai" else "ollama",
        base_url=settings.llm_base_url,
    )
    return instructor.from_openai(openai_client)


# --- Service ---

class DomainInferenceService:
    """Infer likely domain names for a given Companies House company profile."""

    def __init__(self):
        self._client = _build_client()

    async def infer(self, company_data: dict) -> DomainInferenceResult:
        """Generate ranked domain candidates from a CH company profile."""

        prompt = _build_prompt(company_data)

        result = await self._client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at inferring company domain names from "
                        "structured company registration data. You reason carefully "
                        "about likely web presence based on company name, industry, "
                        "and location. You never fabricate — if you are not confident, "
                        "reflect that in your confidence score."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_model=DomainInferenceResult,
            max_retries=2,
        )

        return result


def _build_prompt(company_data: dict) -> str:
    """Extract the most signal-rich fields from a CH profile for the prompt."""

    name = company_data.get("company_name", "Unknown")
    status = company_data.get("company_status", "unknown")
    company_type = company_data.get("type", "unknown")
    created = company_data.get("date_of_creation", "unknown")
    sic_codes = company_data.get("sic_codes", [])
    address = company_data.get("registered_office_address", {})
    locality = address.get("locality", "")
    postcode = address.get("postal_code", "")

    return f"""Given the following UK company registration data, suggest up to 5 likely domain names.

Company name: {name}
Status: {status}
Type: {company_type}
Incorporated: {created}
SIC codes (industry): {", ".join(sic_codes) if sic_codes else "not provided"}
Location: {", ".join(filter(None, [locality, postcode]))}

Consider common domain patterns:
- Direct name mappings (e.g. acme.co.uk, acme.com)
- Abbreviated or shortened versions of the name
- Industry-relevant TLDs (.io, .co.uk, .com)
- Removing common suffixes (Ltd, PLC, Group, Holdings)

Return candidates ranked by confidence, most likely first."""
