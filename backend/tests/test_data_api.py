import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from db.session import Base, get_db
from db.models import Company, Lookup, DomainCandidate, RankingSummary, ChSnapshot, PipelineConfig
from api.main import app

# --- In-memory SQLite test database ---
# StaticPool ensures all connections share the same in-memory database.
# Without it, each new connection gets a fresh empty DB and sees no tables.

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


# --- Fixtures ---

def _make_company(db, company_number="09446231", name="MONZO BANK LIMITED") -> Company:
    company = Company(
        company_number=company_number,
        company_name=name,
        company_status="active",
        company_type="ltd",
        sic_codes=["64191"],
    )
    db.add(company)
    db.flush()
    return company


def _make_lookup(db, company: Company, job_id: str = "test-job-123", status: str = "success") -> Lookup:
    snapshot = ChSnapshot(company_number=company.company_number, data={})
    db.add(snapshot)
    db.flush()

    config = PipelineConfig(
        config_hash="abc123",
        llm_provider="openai",
        llm_model="gpt-4o",
        inference_prompt_version="v1",
        ranking_prompt_version="v1",
        scoring_weights={},
    )
    db.add(config)
    db.flush()

    lookup = Lookup(
        job_id=job_id,
        company_id=company.id,
        ch_snapshot_id=snapshot.id,
        pipeline_config_id=config.id,
        status=status,
        completed_at=datetime.now(timezone.utc) if status == "success" else None,
    )
    db.add(lookup)
    db.flush()
    return lookup


def _make_candidate(db, lookup: Lookup, domain: str, is_primary: bool = False, final_score: float = 0.8) -> DomainCandidate:
    candidate = DomainCandidate(
        lookup_id=lookup.id,
        domain=domain,
        discovered_via_redirect=False,
        llm_confidence=0.9,
        llm_reasoning="test reasoning",
        verification_score=0.7,
        final_score=final_score,
        ranking_confidence=0.85,
        ranking_reasoning="ranking reasoning",
        is_primary_candidate=is_primary,
        is_squatted_or_parked=False,
    )
    db.add(candidate)
    db.flush()
    return candidate


def _make_ranking_summary(db, lookup: Lookup, primary_domain: str) -> RankingSummary:
    summary = RankingSummary(
        lookup_id=lookup.id,
        primary_domain=primary_domain,
        summary="Test summary",
    )
    db.add(summary)
    db.flush()
    return summary


# --- Lookup tests ---

@pytest.mark.asyncio
async def test_list_lookups_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/lookups")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_lookups_returns_entries():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_ranking_summary(db, lookup, "monzo.com")
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/lookups")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["company_name"] == "MONZO BANK LIMITED"
    assert data[0]["primary_domain"] == "monzo.com"


@pytest.mark.asyncio
async def test_get_lookup_returns_candidates():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_candidate(db, lookup, "monzo.com", is_primary=True, final_score=0.95)
    _make_candidate(db, lookup, "monzo.co.uk", final_score=0.70)
    _make_ranking_summary(db, lookup, "monzo.com")
    db.commit()
    lookup_id = lookup.id
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/lookups/{lookup_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 2
    assert data["candidates"][0]["domain"] == "monzo.com"
    assert data["ranking_summary"]["primary_domain"] == "monzo.com"


@pytest.mark.asyncio
async def test_get_lookup_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/lookups/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_verify_lookup_sets_ground_truth():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_candidate(db, lookup, "monzo.com", is_primary=True)
    db.commit()
    lookup_id = lookup.id
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/lookups/{lookup_id}/verify",
            json={"domain": "monzo.com", "verified_by": "human"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["verified_domain"] == "monzo.com"
    assert data["verified_by"] == "human"


@pytest.mark.asyncio
async def test_verify_lookup_rejects_unknown_domain():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_candidate(db, lookup, "monzo.com")
    db.commit()
    lookup_id = lookup.id
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            f"/lookups/{lookup_id}/verify",
            json={"domain": "notacandidate.com", "verified_by": "human"},
        )

    assert response.status_code == 404


# --- Dataset tests ---

@pytest.mark.asyncio
async def test_list_companies_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_company_returns_lookups():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_ranking_summary(db, lookup, "monzo.com")
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies/09446231")

    assert response.status_code == 200
    data = response.json()
    assert data["company_number"] == "09446231"
    assert len(data["lookups"]) == 1
    assert data["lookups"][0]["primary_domain"] == "monzo.com"


@pytest.mark.asyncio
async def test_get_company_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies/99999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_best_domain_returns_primary():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    _make_candidate(db, lookup, "monzo.com", is_primary=True, final_score=0.95)
    _make_candidate(db, lookup, "monzo.co.uk", final_score=0.70)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies/09446231/best")

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "monzo.com"
    assert data["source"] == "automated_ranking"


@pytest.mark.asyncio
async def test_get_best_domain_prefers_human_verified():
    db = TestingSessionLocal()
    company = _make_company(db)
    lookup = _make_lookup(db, company)
    candidate = _make_candidate(db, lookup, "monzo.com", is_primary=True, final_score=0.95)
    lookup.verified_domain_id = candidate.id
    lookup.verified_by = "human"
    lookup.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies/09446231/best")

    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "monzo.com"
    assert data["source"] == "human_verified"


@pytest.mark.asyncio
async def test_get_best_domain_no_lookups():
    db = TestingSessionLocal()
    _make_company(db)
    db.commit()
    db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/dataset/companies/09446231/best")

    assert response.status_code == 404
