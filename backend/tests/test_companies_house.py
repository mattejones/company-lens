import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.companies_house import CompaniesHouseClient

MOCK_SEARCH_RESPONSE = {
    "items": [
        {
            "company_number": "00000006",
            "title": "ACME LTD",
            "company_status": "active",
            "date_of_creation": "2000-01-01",
            "address": {
                "locality": "London",
                "postal_code": "EC1A 1BB",
            },
        }
    ],
    "total_results": 1,
}

MOCK_COMPANY_RESPONSE = {
    "company_number": "00000006",
    "company_name": "ACME LTD",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2000-01-01",
    "registered_office_address": {
        "locality": "London",
        "postal_code": "EC1A 1BB",
    },
}


@pytest.mark.asyncio
async def test_search_returns_results():
    with patch("services.companies_house.settings") as mock_settings:
        mock_settings.ch_api_key = "test-key"
        client = CompaniesHouseClient()

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
            result = await client.search("ACME")
            assert result["total_results"] == 1
            assert result["items"][0]["company_number"] == "00000006"

        await client.close()


@pytest.mark.asyncio
async def test_get_company_returns_profile():
    with patch("services.companies_house.settings") as mock_settings:
        mock_settings.ch_api_key = "test-key"
        client = CompaniesHouseClient()

        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_COMPANY_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_response):
            result = await client.get_company("00000006")
            assert result["company_name"] == "ACME LTD"
            assert result["company_status"] == "active"

        await client.close()
