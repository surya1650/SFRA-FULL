"""Add the audit_event table.

Revision ID: 20260430_0003
Revises: 20260430_0002
Create Date: 2026-04-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260430_0003"
down_revision: Union[str, Sequence[str], None] = "20260430_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACTIONS = (
    "LOGIN", "LOGOUT", "LOGIN_FAILED",
    "TRANSFORMER_CREATE", "TRANSFORMER_UPDATE",
    "CYCLE_OPEN", "CYCLE_CLOSE",
    "SESSION_CREATE",
    "UPLOAD_REFERENCE", "UPLOAD_TESTED", "UPLOAD_REPLACED",
    "ANALYSIS_RUN", "ANALYSIS_REVIEW",
    "REPORT_GENERATE_PDF", "REPORT_GENERATE_XLSX",
    "THRESHOLDS_UPDATE",
    "USER_CREATE", "USER_DEACTIVATE",
)


def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("actor_id", sa.String(32)),
        sa.Column("actor_email", sa.String(255)),
        sa.Column("actor_role", sa.String(16)),
        sa.Column("action", sa.Enum(*ACTIONS, name="audit_action"), nullable=False),
        sa.Column("target_kind", sa.String(32)),
        sa.Column("target_id", sa.String(64)),
        sa.Column("request_method", sa.String(8)),
        sa.Column("request_path", sa.String(512)),
        sa.Column("response_status", sa.Integer()),
        sa.Column("detail", sa.JSON()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_actor_time", "audit_event", ["actor_id", "occurred_at"])
    op.create_index("ix_audit_action_time", "audit_event", ["action", "occurred_at"])
    op.create_index("ix_audit_target", "audit_event", ["target_kind", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_target", table_name="audit_event")
    op.drop_index("ix_audit_action_time", table_name="audit_event")
    op.drop_index("ix_audit_actor_time", table_name="audit_event")
    op.drop_table("audit_event")
