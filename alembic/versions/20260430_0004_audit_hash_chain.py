"""Add tamper-evident hash chain columns to audit_event.

Revision ID: 20260430_0004
Revises: 20260430_0003
Create Date: 2026-04-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260430_0004"
down_revision: Union[str, Sequence[str], None] = "20260430_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch-mode for SQLite compatibility — adding columns to an
    # existing table on SQLite requires a recreate.
    with op.batch_alter_table("audit_event") as batch:
        batch.add_column(sa.Column("prev_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("current_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("audit_event") as batch:
        batch.drop_column("current_hash")
        batch.drop_column("prev_hash")
