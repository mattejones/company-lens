import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Company, Lookup, DomainCandidate, RankingSummary

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/companies")
def list_companies(limit: int = 50, db: Session = Depends(get_db)) -> list[dict]:
    """List all companies in the dataset."""
    companies = (
        db.query(Company)
        .order_by(Company.company_name)
        .limit(limit)
        .all()
    )
    return [_summarise_company(c, db) for c in companies]


@router.get("/companies/{company_number}")
def get_company(company_number: str, db: Session = Depends(get_db)) -> dict:
    """Company detail with all its lookups."""
    company = db.query(Company).filter_by(company_number=company_number).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    lookups = (
        db.query(Lookup)
        .filter_by(company_id=company.id)
        .order_by(Lookup.created_at.desc())
        .all()
    )

    lookup_summaries = []
    for lookup in lookups:
        summary = db.query(RankingSummary).filter_by(lookup_id=lookup.id).first()
        lookup_summaries.append({
            "lookup_id": str(lookup.id),
            "status": lookup.status,
            "created_at": lookup.created_at,
            "completed_at": lookup.completed_at,
            "primary_domain": summary.primary_domain if summary else None,
            "verified_domain_id": str(lookup.verified_domain_id) if lookup.verified_domain_id else None,
            "verified_by": lookup.verified_by,
            "verified_at": lookup.verified_at,
        })

    return {
        "company_number": company.company_number,
        "company_name": company.company_name,
        "company_status": company.company_status,
        "company_type": company.company_type,
        "sic_codes": company.sic_codes,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "lookups": lookup_summaries,
    }


@router.get("/companies/{company_number}/best")
def get_best_domain(company_number: str, db: Session = Depends(get_db)) -> dict:
    """Return the highest confidence primary domain across all lookups for a company.

    Prefers human-verified results over automated ranking.
    """
    company = db.query(Company).filter_by(company_number=company_number).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Check for a human-verified result first
    verified_lookup = (
        db.query(Lookup)
        .filter_by(company_id=company.id, verified_by="human")
        .order_by(Lookup.verified_at.desc())
        .first()
    )
    if verified_lookup and verified_lookup.verified_domain_id:
        candidate = db.query(DomainCandidate).filter_by(
            id=verified_lookup.verified_domain_id
        ).first()
        if candidate:
            return {
                "company_number": company_number,
                "company_name": company.company_name,
                "domain": candidate.domain,
                "source": "human_verified",
                "verified_at": verified_lookup.verified_at,
                "final_score": candidate.final_score,
            }

    # Fall back to highest-scoring primary candidate across all successful lookups
    best = (
        db.query(DomainCandidate)
        .join(Lookup, DomainCandidate.lookup_id == Lookup.id)
        .filter(
            Lookup.company_id == company.id,
            Lookup.status == "success",
            DomainCandidate.is_primary_candidate == True,
        )
        .order_by(DomainCandidate.final_score.desc())
        .first()
    )

    if not best:
        raise HTTPException(status_code=404, detail="No completed lookups found for this company")

    return {
        "company_number": company_number,
        "company_name": company.company_name,
        "domain": best.domain,
        "source": "automated_ranking",
        "final_score": best.final_score,
        "ranking_confidence": best.ranking_confidence,
    }
