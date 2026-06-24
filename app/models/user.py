from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.constants import ACTIVE_STATUS, ROLE_WAITER
from app.models.mixins import TimestampMixin, uuid_str


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('admin', 'waiter', 'cook')", name="ck_users_role"),
        CheckConstraint("status in ('active', 'inactive', 'deleted')", name="ck_users_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    vk_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=ROLE_WAITER)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ACTIVE_STATUS)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    creator: Mapped["User | None"] = relationship(remote_side=[id])
