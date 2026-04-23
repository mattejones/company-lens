from fastapi import APIRouter, HTTPException
from services.domain_inference import DomainInferenceService, DomainInferenceResult
from services.companies_house import CompaniesHouseClient

router = APIRouter(tags=["inference"])


@router.post("/infer", response_model=DomainInferenceResult)
async def infer_domains(company_data: dict) -> DomainInferenceResult:
    """Infer domain candidates from a pre-fetched CH company profile."""
    try:
        service = DomainInferenceService()
        return await service.infer(company_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Inference error: {str(e)}")


@router.get("/companies/{company_number}/infer", response_model=DomainInferenceResult)
async def fetch_and_infer(company_number: str) -> DomainInferenceResult:
    """Convenience wrapper — fetches CH profile then runs domain inference in one call."""
    ch_client = CompaniesHouseClient()
    try:
        company_data = await ch_client.get_company(company_number)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Companies House error: {str(e)}")
    finally:
        await ch_client.close()

    try:
        service = DomainInferenceService()
        return await service.infer(company_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Inference error: {str(e)}")
