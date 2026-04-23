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
        return {
            "company_data": company_data,
            "inference": result.model_dump(),
            "prompts": service.last_prompts,
        }

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
            "inference": inference_payload["inference"],
            "prompts": inference_payload.get("prompts", {}),
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
        return {
            "company_data": verification_payload["company_data"],
            "inference": verification_payload["inference"],
            "prompts": verification_payload.get("prompts", {}),
            "verification": verification_payload["verification"],
            "ranking": result.model_dump(),
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def persist_results_task(self, pipeline_payload: dict, job_id: str) -> dict:
    """Persist all pipeline results to PostgreSQL."""
    from db.session import SessionLocal
    from db.repository import (
        get_or_create_pipeline_config,
        get_or_create_company,
        create_ch_snapshot,
        create_lookup,
        create_inference_result,
        create_domain_candidates,
        create_ranking_summary,
        complete_lookup,
        fail_lookup,
    )

    db = SessionLocal()
    try:
        company_data = pipeline_payload["company_data"]
        inference = pipeline_payload["inference"]
        prompts = pipeline_payload.get("prompts", {})
        verification = pipeline_payload["verification"]
        ranking = pipeline_payload["ranking"]

        pipeline_config = get_or_create_pipeline_config(db)
        company = get_or_create_company(db, company_data)
        snapshot = create_ch_snapshot(db, company_data)
        lookup = create_lookup(db, job_id, company, snapshot, pipeline_config)

        create_inference_result(
            db, lookup,
            candidates_raw=inference,
            system_prompt=prompts.get("system", ""),
            user_prompt=prompts.get("user", ""),
        )

        candidates = create_domain_candidates(
            db, lookup,
            verification_candidates=verification.get("candidates", []),
            ranking_candidates=ranking.get("candidates", []),
        )

        create_ranking_summary(db, lookup, candidates, ranking)
        complete_lookup(db, job_id)
        db.commit()

        return {"persisted": True, "lookup_id": str(lookup.id)}

    except Exception as exc:
        db.rollback()
        fail_lookup(db, job_id)
        db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
