"""Add the ``user`` table for Phase 2.3 auth scaffold.

Revision ID: 20260430_0002
Revises: 20260426_0001
Create Date: 2026-04-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260430_0002"
down_revision: Union[str, Sequence[str], None] = "20260426_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLES = ("ENGINEER", "REVIEWER", "ADMIN")


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(160)),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum(*ROLES, name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("user")
