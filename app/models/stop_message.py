from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, uuid_str


json_type = JSON().with_variant(JSONB, "postgresql")


class StopMessage(TimestampMixin, Base):
    __tablename__ = "stop_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    broadcast_payload: Mapped[dict | None] = mapped_column(json_type)

    author: Mapped["User"] = relationship("User")
