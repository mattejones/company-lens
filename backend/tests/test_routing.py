"""
Routing integrity tests.

These exist specifically to catch the recurring double-prefix bug where
main.py adds prefix="/companies" to a router that already defines it internally,
resulting in routes like /companies/companies/search instead of /companies/search.

If any of these tests fail, check api/main.py — do NOT pass prefix= when
including a router that already defines its own prefix.
"""
from api.main import app


def _routes() -> list[str]:
    return [r.path for r in app.routes]


def test_companies_search_route_is_not_doubled():
    routes = _routes()
    assert "/companies/search" in routes, "Missing /companies/search"
    assert "/companies/companies/search" not in routes, "Double prefix on companies router"


def test_companies_number_route_is_not_doubled():
    routes = _routes()
    assert "/companies/{company_number}" in routes
    assert "/companies/companies/{company_number}" not in routes


def test_infer_route_exists():
    routes = _routes()
    assert "/companies/{company_number}/infer" in routes


def test_jobs_routes_exist():
    routes = _routes()
    assert "/jobs" in routes
    assert "/jobs/{job_id}" in routes


def test_lookups_routes_exist():
    routes = _routes()
    assert "/lookups" in routes
    assert "/lookups/{lookup_id}" in routes


def test_dataset_routes_exist():
    routes = _routes()
    assert "/dataset/companies" in routes
    assert "/dataset/companies/{company_number}" in routes
    assert "/dataset/companies/{company_number}/best" in routes


def test_health_route_exists():
    assert "/health" in _routes()
