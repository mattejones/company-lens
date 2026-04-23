from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from workers.celery_app import celery_app
from utils.job_registry import get_job_metadata, list_job_ids

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(limit: int = 50) -> list[dict]:
    """Return the most recent jobs with their current status."""
    job_ids = list_job_ids(limit)
    jobs = []
    for job_id in job_ids:
        metadata = get_job_metadata(job_id)
        result = AsyncResult(job_id, app=celery_app)
        entry = {**metadata, "status": result.status}
        if result.successful():
            raw = result.get()
            entry["lookup_id"] = raw.get("lookup_id")
        jobs.append(entry)
    return jobs


@router.get("/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Poll the status of a pipeline job by ID."""
    metadata = get_job_metadata(job_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    result = AsyncResult(job_id, app=celery_app)

    response = {
        **metadata,
        "status": result.status,
        "lookup_id": None,
        "error": None,
    }

    if result.successful():
        raw = result.get()
        response["lookup_id"] = raw.get("lookup_id")
    elif result.failed():
        response["error"] = str(result.result)

    return response
