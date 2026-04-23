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
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def infer_domains_task(self, company_data: dict) -> dict:
    """Run LLM domain inference against a CH company profile."""
    from services.domain_inference import DomainInferenceService

    async def _run():
        service = DomainInferenceService()
        result = await service.infer(company_data)
        return result.model_dump()

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def verify_domains_task(self, inference_result: dict) -> dict:
    """Verify domain candidates via DNS, WHOIS, and HTTP checks."""
    from services.verification import VerificationService

    async def _run():
        service = VerificationService()
        result = await service.verify(inference_result)
        return result.model_dump()

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
