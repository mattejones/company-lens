import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class InferenceResult(Base):
    """Stage 1 LLM output — preserved verbatim before verification.

    Allows independent evaluation of inference quality vs verification
    quality. The rendered prompt is stored so results are reproducible
    even if the template changes.
    """
    __tablename__ = "inference_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lookup_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lookups.id"), nullable=False, unique=True
    )
    candidates_raw: Mapped[dict] = mapped_column(JSON, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
