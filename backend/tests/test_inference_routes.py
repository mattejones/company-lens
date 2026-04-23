import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from api.main import app

MOCK_COMPANY = {
    "company_name": "MONZO BANK LIMITED",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2015-06-01",
    "sic_codes": ["64191"],
    "registered_office_address": {
        "locality": "London",
        "postal_code": "EC2V 7NQ",
    },
}

MOCK_JOB_METADATA = {
    "job_id": "test-job-123",
    "type": "fetch_and_infer",
    "company_number": "09446231",
    "created_at": "2024-01-01T00:00:00+00:00",
}

FIXED_UUID = "test-job-123"


def _mock_chain():
    mock_chain = MagicMock()
    mock_chain.apply_async.return_value = MagicMock()
    return mock_chain


@pytest.mark.asyncio
async def test_post_infer_returns_job_id():
    with patch("api.routes.inference.chain", return_value=_mock_chain()), \
         patch("api.routes.inference.register_job"), \
         patch("api.routes.inference.uuid.uuid4", return_value=FIXED_UUID):

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/infer", json=MOCK_COMPANY)

        assert response.status_code == 200
        assert response.json()["job_id"] == FIXED_UUID


@pytest.mark.asyncio
async def test_fetch_and_infer_returns_job_id():
    with patch("api.routes.inference.chain", return_value=_mock_chain()), \
         patch("api.routes.inference.register_job"), \
         patch("api.routes.inference.uuid.uuid4", return_value=FIXED_UUID):

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/companies/09446231/infer")

        assert response.status_code == 200
        assert response.json()["job_id"] == FIXED_UUID


@pytest.mark.asyncio
async def test_job_status_success():
    with patch("api.routes.jobs.get_job_metadata", return_value=MOCK_JOB_METADATA), \
         patch("api.routes.jobs.AsyncResult") as mock_async_result:
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.successful.return_value = True
        mock_result.failed.return_value = False
        mock_result.get.return_value = {"candidates": []}
        mock_async_result.return_value = mock_result

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/jobs/test-job-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["result"] == {"candidates": []}


@pytest.mark.asyncio
async def test_job_status_pending():
    with patch("api.routes.jobs.get_job_metadata", return_value=MOCK_JOB_METADATA), \
         patch("api.routes.jobs.AsyncResult") as mock_async_result:
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_result.successful.return_value = False
        mock_result.failed.return_value = False
        mock_async_result.return_value = mock_result

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/jobs/test-job-pending")

        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"
        assert response.json()["result"] is None


@pytest.mark.asyncio
async def test_job_status_not_found():
    with patch("api.routes.jobs.get_job_metadata", return_value=None):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/jobs/bogus-id")

        assert response.status_code == 404
