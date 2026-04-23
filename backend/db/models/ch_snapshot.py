import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class ChSnapshot(Base):
    """Immutable snapshot of CH API data at the time of a lookup.

    Never updated. Each lookup gets its own snapshot so results are
    always reproducible — we can always answer 'what data did the
    LLM actually see?'
    """
    __tablename__ = "ch_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
