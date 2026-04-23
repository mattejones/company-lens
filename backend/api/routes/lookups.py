import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Lookup, DomainCandidate, RankingSummary, Company

router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("")
def list_lookups(limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    """List all lookups with summary information."""
    lookups = (
        db.query(Lookup)
        .order_by(Lookup.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_summarise_lookup(l, db) for l in lookups]


@router.get("/{lookup_id}")
def get_lookup(lookup_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Full lookup detail including all candidates and ranking summary."""
    lookup = db.query(Lookup).filter_by(id=lookup_id).first()
    if not lookup:
        raise HTTPException(status_code=404, detail="Lookup not found")

    company = db.query(Company).filter_by(id=lookup.company_id).first()
    summary = db.query(RankingSummary).filter_by(lookup_id=lookup_id).first()
    candidates = (
        db.query(DomainCandidate)
        .filter_by(lookup_id=lookup_id)
        .order_by(DomainCandidate.final_score.desc())
        .all()
    )

    return {
        "lookup_id": str(lookup.id),
        "job_id": lookup.job_id,
        "status": lookup.status,
        "created_at": lookup.created_at,
        "completed_at": lookup.completed_at,
        "company": {
            "company_number": company.company_number if company else None,
            "company_name": company.company_name if company else None,
        },
        "ranking_summary": {
            "primary_domain": summary.primary_domain if summary else None,
            "summary": summary.summary if summary else None,
        } if summary else None,
        "verified_domain_id": str(lookup.verified_domain_id) if lookup.verified_domain_id else None,
        "verified_by": lookup.verified_by,
        "verified_at": lookup.verified_at,
        "candidates": [_serialise_candidate(c) for c in candidates],
    }


@router.get("/{lookup_id}/candidates")
def list_candidates(lookup_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    """All domain candidates for a lookup, ranked by final score."""
    lookup = db.query(Lookup).filter_by(id=lookup_id).first()
    if not lookup:
        raise HTTPException(status_code=404, detail="Lookup not found")

    candidates = (
        db.query(DomainCandidate)
        .filter_by(lookup_id=lookup_id)
        .order_by(DomainCandidate.final_score.desc())
        .all()
    )
    return [_serialise_candidate(c) for c in candidates]


@router.put("/{lookup_id}/verify")
def verify_lookup(
    lookup_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    """Set the ground truth verified domain for a lookup."""
    lookup = db.query(Lookup).filter_by(id=lookup_id).first()
    if not lookup:
        raise HTTPException(status_code=404, detail="Lookup not found")

    domain = payload.get("domain")
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")

    candidate = (
        db.query(DomainCandidate)
        .filter_by(lookup_id=lookup_id, domain=domain)
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=404,
            detail=f"Domain {domain} not found in candidates for this lookup"
        )

    lookup.verified_domain_id = candidate.id
    lookup.verified_by = payload.get("verified_by", "human")
    lookup.verified_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "lookup_id": str(lookup_id),
        "verified_domain": domain,
        "verified_by": lookup.verified_by,
        "verified_at": lookup.verified_at,
    }


def _summarise_lookup(lookup: Lookup, db: Session) -> dict:
    company = db.query(Company).filter_by(id=lookup.company_id).first()
    summary = db.query(RankingSummary).filter_by(lookup_id=lookup.id).first()
    return {
        "lookup_id": str(lookup.id),
        "job_id": lookup.job_id,
        "status": lookup.status,
        "created_at": lookup.created_at,
        "completed_at": lookup.completed_at,
        "company_name": company.company_name if company else None,
        "company_number": company.company_number if company else None,
        "primary_domain": summary.primary_domain if summary else None,
        "verified_domain_id": str(lookup.verified_domain_id) if lookup.verified_domain_id else None,
    }


def _serialise_candidate(c: DomainCandidate) -> dict:
    return {
        "id": str(c.id),
        "domain": c.domain,
        "discovered_via_redirect": c.discovered_via_redirect,
        "llm_confidence": c.llm_confidence,
        "llm_reasoning": c.llm_reasoning,
        "verification_score": c.verification_score,
        "final_score": c.final_score,
        "ranking_confidence": c.ranking_confidence,
        "ranking_reasoning": c.ranking_reasoning,
        "is_primary_candidate": c.is_primary_candidate,
        "is_squatted_or_parked": c.is_squatted_or_parked,
        "dns_data": c.dns_data,
        "https_data": c.https_data,
        "ssl_data": c.ssl_data,
        "whois_data": c.whois_data,
        "content_data": c.content_data,
        "created_at": c.created_at,
    }
