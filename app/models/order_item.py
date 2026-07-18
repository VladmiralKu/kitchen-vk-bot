from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.constants import ITEM_PENDING
from app.models.mixins import TimestampMixin, uuid_str


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    position_index: Mapped[int] = mapped_column(Integer, nullable=False)
    course: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ITEM_PENDING)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    ready_seconds: Mapped[int | None] = mapped_column(Integer)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    ready_by_user: Mapped["User | None"] = relationship("User")
