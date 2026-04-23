import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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


@pytest.mark.asyncio
async def test_infer_returns_candidates():
    with patch("services.domain_inference._build_client") as mock_build:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MOCK_INFERENCE_RESULT)
        mock_build.return_value = mock_client

        service = DomainInferenceService()
        result = await service.infer(MOCK_COMPANY)

        assert len(result.candidates) == 3
        assert result.candidates[0].domain == "acmetechnologies.co.uk"
        assert result.candidates[0].confidence == 0.85


@pytest.mark.asyncio
async def test_infer_candidates_ordered_by_confidence():
    with patch("services.domain_inference._build_client") as mock_build:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MOCK_INFERENCE_RESULT)
        mock_build.return_value = mock_client

        service = DomainInferenceService()
        result = await service.infer(MOCK_COMPANY)

        confidences = [c.confidence for c in result.candidates]
        assert confidences == sorted(confidences, reverse=True)


@pytest.mark.asyncio
async def test_infer_called_with_correct_model():
    with patch("services.domain_inference._build_client") as mock_build:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MOCK_INFERENCE_RESULT)
        mock_build.return_value = mock_client

        service = DomainInferenceService()
        await service.infer(MOCK_COMPANY)

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_model"] == DomainInferenceResult
