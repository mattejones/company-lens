import asyncio
from workers.celery_app import celery_app
from services.companies_house import CompaniesHouseClient


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def fetch_company_task(self, company_number: str) -> dict:
    """Fetch a company profile from Companies House."""
    async def _run():
        client = CompaniesHouseClient()
        try:
            return await client.get_company(company_number)
        finally:
            await client.close()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def infer_domains_task(self, company_data: dict) -> dict:
    """Run LLM domain inference against a CH company profile."""
    from services.domain_inference import DomainInferenceService

    async def _run():
        service = DomainInferenceService()
        result = await service.infer(company_data)
        return {"company_data": company_data, "inference": result.model_dump()}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def verify_domains_task(self, inference_payload: dict) -> dict:
    """Verify domain candidates via DNS, WHOIS, HTTPS, SSL, and content checks."""
    from services.verification import VerificationService

    async def _run():
        company_data = inference_payload["company_data"]
        company_name = company_data.get("company_name", "")
        service = VerificationService(company_name=company_name)
        result = await service.verify(inference_payload["inference"], company_name)
        return {
            "company_data": company_data,
            "verification": result.model_dump(),
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def rank_domains_task(self, verification_payload: dict) -> dict:
    """Stage 2 LLM — re-rank verified candidates using structured evidence."""
    from services.domain_ranking import DomainRankingService

    async def _run():
        service = DomainRankingService()
        result = await service.rank(
            verification_payload["company_data"],
            verification_payload["verification"],
        )
        return result.model_dump()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
