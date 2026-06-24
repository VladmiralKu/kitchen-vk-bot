from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.constants import ORDER_NEW
from app.models.mixins import TimestampMixin, uuid_str


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_no: Mapped[int] = mapped_column(BigInteger, Identity(start=1), unique=True, index=True)
    waiter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    table_number: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ORDER_NEW, index=True)
    sent_to_kitchen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    total_ready_seconds: Mapped[int | None] = mapped_column(Integer)

    waiter: Mapped["User"] = relationship("User", foreign_keys=[waiter_id])
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.position_index",
    )
