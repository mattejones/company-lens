from celery import chain
from fastapi import APIRouter, HTTPException
from workers.tasks.pipeline import fetch_company_task, infer_domains_task, verify_domains_task
from utils.job_registry import register_job

router = APIRouter(tags=["inference"])


@router.post("/infer")
async def infer_domains(company_data: dict) -> dict:
    """Dispatch inference + verification pipeline for pre-fetched CH data.

    Returns a job ID immediately — poll /jobs/{job_id} for results.
    """
    try:
        job = chain(
            infer_domains_task.s(company_data),
            verify_domains_task.s(),
        ).apply_async()
        register_job(job.id, {
            "type": "infer",
            "company_name": company_data.get("company_name", "unknown"),
        })
        return {"job_id": job.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch job: {str(e)}")


@router.get("/companies/{company_number}/infer")
async def fetch_and_infer(company_number: str) -> dict:
    """Convenience wrapper — chains CH fetch, inference, and verification.

    Returns a job ID immediately — poll /jobs/{job_id} for results.
    """
    try:
        job = chain(
            fetch_company_task.s(company_number),
            infer_domains_task.s(),
            verify_domains_task.s(),
        ).apply_async()
        register_job(job.id, {
            "type": "fetch_and_infer",
            "company_number": company_number,
        })
        return {"job_id": job.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch job: {str(e)}")
