import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.domain_inference import DomainInferenceService, DomainCandidate, DomainInferenceResult

MOCK_COMPANY = {
    "company_name": "ACME TECHNOLOGIES LTD",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2015-06-01",
    "sic_codes": ["62012"],
    "registered_office_address": {
        "locality": "London",
        "postal_code": "EC1A 1BB",
    },
}

MOCK_INFERENCE_RESULT = DomainInferenceResult(
    candidates=[
        DomainCandidate(domain="acmetechnologies.co.uk", reasoning="Direct name mapping with UK TLD", confidence=0.85),
        DomainCandidate(domain="acmetech.io", reasoning="Shortened name with tech-relevant TLD", confidence=0.65),
        DomainCandidate(domain="acme.co.uk", reasoning="Abbreviated name with UK TLD", confidence=0.50),
    ]
)


def _mock_adapter(result):
    """Build a mock LLM adapter that returns the given result."""
    mock = MagicMock()
    mock.complete = AsyncMock(return_value=result)
    return mock


@pytest.mark.asyncio
async def test_infer_returns_candidates():
    with patch("services.domain_inference.build_llm_adapter", return_value=_mock_adapter(MOCK_INFERENCE_RESULT)):
        service = DomainInferenceService()
        result = await service.infer(MOCK_COMPANY)

        assert len(result.candidates) == 3
        assert result.candidates[0].domain == "acmetechnologies.co.uk"
        assert result.candidates[0].confidence == 0.85


@pytest.mark.asyncio
async def test_infer_candidates_ordered_by_confidence():
    with patch("services.domain_inference.build_llm_adapter", return_value=_mock_adapter(MOCK_INFERENCE_RESULT)):
        service = DomainInferenceService()
        result = await service.infer(MOCK_COMPANY)

        confidences = [c.confidence for c in result.candidates]
        assert confidences == sorted(confidences, reverse=True)


@pytest.mark.asyncio
async def test_infer_called_with_correct_prompts():
    mock_adapter = _mock_adapter(MOCK_INFERENCE_RESULT)

    with patch("services.domain_inference.build_llm_adapter", return_value=mock_adapter):
        service = DomainInferenceService()
        await service.infer(MOCK_COMPANY)

        mock_adapter.complete.assert_called_once()
        call_kwargs = mock_adapter.complete.call_args.kwargs
        assert call_kwargs["response_model"] == DomainInferenceResult
        assert "system_prompt" in call_kwargs
        assert "user_prompt" in call_kwargs
        # Verify company name appears in the rendered user prompt
        assert "ACME TECHNOLOGIES" in call_kwargs["user_prompt"]
