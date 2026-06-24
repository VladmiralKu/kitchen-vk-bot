from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, uuid_str


json_type = JSON().with_variant(JSONB, "postgresql")


class OrderEvent(TimestampMixin, Base):
    __tablename__ = "order_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    item_id: Mapped[str | None] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict | None] = mapped_column(json_type)
    vk_event_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)

    order: Mapped["Order | None"] = relationship("Order")
    item: Mapped["OrderItem | None"] = relationship("OrderItem")
    user: Mapped["User | None"] = relationship("User")
