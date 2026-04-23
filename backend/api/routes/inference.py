import uuid
from celery import chain
from fastapi import APIRouter, HTTPException
from workers.tasks.pipeline import (
    fetch_company_task,
    infer_domains_task,
    verify_domains_task,
    rank_domains_task,
    persist_results_task,
)
from utils.job_registry import register_job

router = APIRouter(tags=["inference"])


@router.post("/infer")
async def infer_domains(company_data: dict) -> dict:
    """Dispatch inference + verification + ranking + persistence pipeline."""
    try:
        job_id = str(uuid.uuid4())
        chain(
            infer_domains_task.s(company_data),
            verify_domains_task.s(),
            rank_domains_task.s(),
            persist_results_task.s(job_id=job_id),
        ).apply_async(task_id=job_id)
        register_job(job_id, {
            "type": "infer",
            "company_name": company_data.get("company_name", "unknown"),
        })
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch job: {str(e)}")


@router.get("/companies/{company_number}/infer")
async def fetch_and_infer(company_number: str) -> dict:
    """Convenience wrapper — chains CH fetch through to persistence."""
    try:
        job_id = str(uuid.uuid4())
        chain(
            fetch_company_task.s(company_number),
            infer_domains_task.s(),
            verify_domains_task.s(),
            rank_domains_task.s(),
            persist_results_task.s(job_id=job_id),
        ).apply_async(task_id=job_id)
        register_job(job_id, {
            "type": "fetch_and_infer",
            "company_number": company_number,
        })
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch job: {str(e)}")
