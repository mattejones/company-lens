import json
from datetime import datetime, timezone
from redis import Redis
from api.config import settings

JOB_KEY_PREFIX = "company_lens:job:"
JOB_INDEX_KEY = "company_lens:jobs"


def _get_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def register_job(job_id: str, metadata: dict) -> None:
    """Store job metadata in Redis and add to the job index."""
    r = _get_redis()
    payload = {
        **metadata,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r.set(f"{JOB_KEY_PREFIX}{job_id}", json.dumps(payload))
    r.lpush(JOB_INDEX_KEY, job_id)


def get_job_metadata(job_id: str) -> dict | None:
    """Retrieve stored metadata for a job ID. Returns None if not found."""
    r = _get_redis()
    raw = r.get(f"{JOB_KEY_PREFIX}{job_id}")
    return json.loads(raw) if raw else None


def list_job_ids(limit: int = 50) -> list[str]:
    """Return the most recent job IDs up to limit."""
    r = _get_redis()
    return r.lrange(JOB_INDEX_KEY, 0, limit - 1)
