from fastapi import APIRouter, HTTPException
from services.companies_house import CompaniesHouseClient

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/search")
async def search_companies(q: str, items_per_page: int = 10):
    """Search for companies by name or registration number."""
    client = CompaniesHouseClient()
    try:
        results = await client.search(q, items_per_page)
        return results
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Companies House error: {str(e)}")
    finally:
        await client.close()


@router.get("/{company_number}")
async def get_company(company_number: str):
    """Fetch a company profile by registration number."""
    client = CompaniesHouseClient()
    try:
        result = await client.get_company(company_number)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Companies House error: {str(e)}")
    finally:
        await client.close()
