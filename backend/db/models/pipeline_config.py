import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class PipelineConfig(Base):
    """Immutable snapshot of pipeline configuration at time of a lookup.

    Captures the LLM model, prompt versions, and scoring weights so that
    results from different pipeline versions remain comparable and auditable.
    Reused across lookups if config is identical — deduplicated by config_hash.
    """
    __tablename__ = "pipeline_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    config_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    llm_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    inference_prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    ranking_prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    scoring_weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
