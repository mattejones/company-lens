import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class DomainCandidate(Base):
    """A single domain candidate from a lookup, with all verification signals.

    All nested signal data (DNS, HTTPS, SSL, WHOIS, content) is stored as
    JSONB to preserve full diagnostic fidelity without schema migrations
    as signals evolve.
    """
    __tablename__ = "domain_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lookup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lookups.id"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    discovered_via_redirect: Mapped[bool] = mapped_column(Boolean, default=False)

    # Stage 1 signals
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification signals
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Stage 2 ranking signals
    ranking_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_squatted_or_parked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Full diagnostic data as JSONB
    dns_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    https_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ssl_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    whois_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
