import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from api.main import app
from services.domain_inference import DomainCandidate, DomainInferenceResult

MOCK_COMPANY = {
    "company_name": "MONZO BANK LIMITED",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2015-06-01",
    "sic_codes": ["64191"],
    "registered_office_address": {
        "locality": "London",
        "postal_code": "EC2V 7NQ",
    },
}

MOCK_RESULT = DomainInferenceResult(
    candidates=[
        DomainCandidate(domain="monzo.com", reasoning="Direct name mapping", confidence=0.95),
        DomainCandidate(domain="monzobank.co.uk", reasoning="Full name with UK TLD", confidence=0.60),
    ]
)


@pytest.mark.asyncio
async def test_post_infer_returns_candidates():
    with patch("api.routes.inference.DomainInferenceService") as mock_service_cls:
        mock_service = MagicMock()
        mock_service.infer = AsyncMock(return_value=MOCK_RESULT)
        mock_service_cls.return_value = mock_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/infer", json=MOCK_COMPANY)

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 2
        assert data["candidates"][0]["domain"] == "monzo.com"


@pytest.mark.asyncio
async def test_fetch_and_infer_chains_services():
    with patch("api.routes.inference.CompaniesHouseClient") as mock_ch_cls, \
         patch("api.routes.inference.DomainInferenceService") as mock_service_cls:

        mock_ch = MagicMock()
        mock_ch.get_company = AsyncMock(return_value=MOCK_COMPANY)
        mock_ch.close = AsyncMock()
        mock_ch_cls.return_value = mock_ch

        mock_service = MagicMock()
        mock_service.infer = AsyncMock(return_value=MOCK_RESULT)
        mock_service_cls.return_value = mock_service

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/companies/12345678/infer")

        assert response.status_code == 200
        mock_ch.get_company.assert_called_once_with("12345678")
        mock_service.infer.assert_called_once_with(MOCK_COMPANY)
