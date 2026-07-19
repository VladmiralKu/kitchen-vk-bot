"""add course to order items

Revision ID: 20260718_0002
Revises: 20260624_0001
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa


revision = "20260718_0002"
down_revision = "20260624_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("order_items")}

    if "course" not in columns:
        op.add_column("order_items", sa.Column("course", sa.Integer(), server_default="1", nullable=False))

    op.alter_column("order_items", "course", server_default=None)


def downgrade() -> None:
    op.drop_column("order_items", "course")
