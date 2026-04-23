import httpx
from api.config import settings

CH_BASE_URL = "https://api.company-information.service.gov.uk"


class CompaniesHouseClient:
    """Client for the Companies House API.

    Authentication uses HTTP Basic Auth with the API key as the username
    and an empty password, as per CH API documentation.
    """

    def __init__(self):
        self._client = httpx.AsyncClient(
            base_url=CH_BASE_URL,
            auth=(settings.ch_api_key, ""),
            timeout=10.0,
        )

    async def search(self, query: str, items_per_page: int = 10) -> dict:
        """Search for companies by name or registration number."""
        response = await self._client.get(
            "/search/companies",
            params={"q": query, "items_per_page": items_per_page},
        )
        response.raise_for_status()
        return response.json()

    async def get_company(self, company_number: str) -> dict:
        """Fetch full company profile by registration number."""
        response = await self._client.get(f"/company/{company_number}")
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self._client.aclose()
