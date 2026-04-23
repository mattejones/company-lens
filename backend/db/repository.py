import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from db.models import (
    Company,
    ChSnapshot,
    PipelineConfig,
    Lookup,
    InferenceResult,
    DomainCandidate,
    RankingSummary,
)
from api.config import settings


# --- Pipeline config ---

SCORING_WEIGHTS = {
    "mx": 0.30,
    "a_record": 0.10,
    "https_live": 0.15,
    "ssl_org_match": 0.15,
    "content_match": 0.15,
    "redirect_to_candidate_penalty": -0.25,
    "redirect_canonical_boost": 0.10,
    "redirect_unknown_penalty": -0.35,
    "parked_penalty": -0.50,
    "llm_confidence_weight": 0.40,
    "verification_weight": 0.60,
}


def _prompt_version(template_name: str) -> str:
    """Derive a version string from the prompt file content hash."""
    from utils.prompts import PROMPTS_DIR
    path = PROMPTS_DIR / template_name
    try:
        content = path.read_text()
        return hashlib.sha256(content.encode()).hexdigest()[:8]
    except FileNotFoundError:
        return "unknown"


def _config_hash(llm_provider: str, llm_model: str, inference_v: str, ranking_v: str, weights: dict) -> str:
    payload = json.dumps({
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "inference_prompt_version": inference_v,
        "ranking_prompt_version": ranking_v,
        "scoring_weights": weights,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:64]


def get_or_create_pipeline_config(db: Session) -> PipelineConfig:
    inference_v = _prompt_version("domain_inference_user.j2")
    ranking_v = _prompt_version("domain_ranking_user.j2")
    chash = _config_hash(
        settings.llm_provider, settings.llm_model,
        inference_v, ranking_v, SCORING_WEIGHTS
    )

    config = db.query(PipelineConfig).filter_by(config_hash=chash).first()
    if config:
        return config

    config = PipelineConfig(
        config_hash=chash,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        inference_prompt_version=inference_v,
        ranking_prompt_version=ranking_v,
        scoring_weights=SCORING_WEIGHTS,
    )
    db.add(config)
    db.flush()
    return config


# --- Company ---

def get_or_create_company(db: Session, ch_data: dict) -> Company:
    company_number = ch_data.get("company_number", "")
    company = db.query(Company).filter_by(company_number=company_number).first()

    if company:
        company.company_name = ch_data.get("company_name", company.company_name)
        company.company_status = ch_data.get("company_status")
        company.company_type = ch_data.get("type")
        company.sic_codes = ch_data.get("sic_codes")
        company.updated_at = datetime.now(timezone.utc)
    else:
        company = Company(
            company_number=company_number,
            company_name=ch_data.get("company_name", ""),
            company_status=ch_data.get("company_status"),
            company_type=ch_data.get("type"),
            sic_codes=ch_data.get("sic_codes"),
        )
        db.add(company)

    db.flush()
    return company


# --- CH Snapshot ---

def create_ch_snapshot(db: Session, ch_data: dict) -> ChSnapshot:
    snapshot = ChSnapshot(
        company_number=ch_data.get("company_number", ""),
        data=ch_data,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


# --- Lookup ---

def create_lookup(
    db: Session,
    job_id: str,
    company: Company,
    snapshot: ChSnapshot,
    pipeline_config: PipelineConfig,
) -> Lookup:
    lookup = Lookup(
        job_id=job_id,
        company_id=company.id,
        ch_snapshot_id=snapshot.id,
        pipeline_config_id=pipeline_config.id,
        status="pending",
    )
    db.add(lookup)
    db.flush()
    return lookup


def complete_lookup(db: Session, job_id: str) -> Lookup | None:
    lookup = db.query(Lookup).filter_by(job_id=job_id).first()
    if lookup:
        lookup.status = "success"
        lookup.completed_at = datetime.now(timezone.utc)
        db.flush()
    return lookup


def fail_lookup(db: Session, job_id: str) -> Lookup | None:
    lookup = db.query(Lookup).filter_by(job_id=job_id).first()
    if lookup:
        lookup.status = "failure"
        lookup.completed_at = datetime.now(timezone.utc)
        db.flush()
    return lookup


# --- Inference result ---

def create_inference_result(
    db: Session,
    lookup: Lookup,
    candidates_raw: dict,
    system_prompt: str,
    user_prompt: str,
) -> InferenceResult:
    result = InferenceResult(
        lookup_id=lookup.id,
        candidates_raw=candidates_raw,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    db.add(result)
    db.flush()
    return result


# --- Domain candidates ---

def create_domain_candidates(
    db: Session,
    lookup: Lookup,
    verification_candidates: list[dict],
    ranking_candidates: list[dict],
) -> list[DomainCandidate]:
    """Merge verification and ranking data into domain candidate rows."""
    ranking_map = {r["domain"]: r for r in ranking_candidates}
    created = []

    for v in verification_candidates:
        domain = v["domain"]
        r = ranking_map.get(domain, {})

        candidate = DomainCandidate(
            lookup_id=lookup.id,
            domain=domain,
            discovered_via_redirect=v.get("discovered_via_redirect", False),
            llm_confidence=v.get("confidence"),
            llm_reasoning=v.get("reasoning"),
            verification_score=v.get("verification_score"),
            final_score=v.get("final_score"),
            ranking_confidence=r.get("confidence"),
            ranking_reasoning=r.get("reasoning"),
            is_primary_candidate=r.get("is_primary_candidate", False),
            is_squatted_or_parked=r.get("is_squatted_or_parked", False),
            dns_data={
                "mx_record": v.get("mx_record"),
                "a_record": v.get("a_record"),
                "nameservers": v.get("nameservers"),
                "is_parked": v.get("is_parked"),
            },
            https_data={
                "live": v.get("https_live"),
                "status_code": v.get("https_status_code"),
                "redirect_domain": v.get("https_redirect_domain"),
                "redirects_to_candidate": v.get("redirects_to_candidate"),
            },
            ssl_data=v.get("ssl_info"),
            whois_data=v.get("whois_data"),
            content_data={
                "signals": v.get("content_signals"),
                "match_score": v.get("content_match_score"),
            },
        )
        db.add(candidate)
        created.append(candidate)

    db.flush()
    return created


# --- Ranking summary ---

def create_ranking_summary(
    db: Session,
    lookup: Lookup,
    candidates: list[DomainCandidate],
    ranking_result: dict,
) -> RankingSummary:
    primary_domain = next(
        (c["domain"] for c in ranking_result.get("candidates", []) if c.get("is_primary_candidate")),
        None,
    )
    primary_candidate = next(
        (c for c in candidates if c.domain == primary_domain), None
    )

    summary = RankingSummary(
        lookup_id=lookup.id,
        primary_domain_id=primary_candidate.id if primary_candidate else None,
        primary_domain=primary_domain,
        summary=ranking_result.get("summary", ""),
    )
    db.add(summary)
    db.flush()
    return summary
