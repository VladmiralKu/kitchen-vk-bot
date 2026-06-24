from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, uuid_str


class VKMessage(TimestampMixin, Base):
    __tablename__ = "vk_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    peer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    conversation_message_id: Mapped[int | None] = mapped_column(BigInteger)
    message_kind: Mapped[str] = mapped_column(String(64), nullable=False)

    order: Mapped["Order | None"] = relationship("Order")
    user: Mapped["User | None"] = relationship("User")
