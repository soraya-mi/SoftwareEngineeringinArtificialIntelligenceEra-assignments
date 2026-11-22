"""initial change request schema

Revision ID: 0001
Revises:
Create Date: 2026-11-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "change_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "requester_id",
            sa.String(length=255),
            sa.ForeignKey("user_accounts.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Uuid(), nullable=False),
        sa.Column("latest_reviewed_revision_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('Draft','PendingReview','Approved','ChangesRequested')",
            name="ck_change_requests_status",
        ),
    )
    op.create_index(
        "ix_change_requests_status_requester",
        "change_requests",
        ["status", "requester_id"],
    )
    op.create_table(
        "user_role_assignments",
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(length=32), primary_key=True),
    )
    op.create_table(
        "change_request_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "change_request_id",
            sa.Uuid(),
            sa.ForeignKey("change_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "submitted_by",
            sa.String(length=255),
            sa.ForeignKey("user_accounts.id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "change_request_id",
            "revision_number",
            name="uq_revision_request_number",
        ),
    )
    op.create_table(
        "change_request_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "change_request_id",
            sa.Uuid(),
            sa.ForeignKey("change_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(length=255),
            sa.ForeignKey("user_accounts.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column(
            "reviewed_revision_id",
            sa.Uuid(),
            sa.ForeignKey("change_request_revisions.id"),
            nullable=True,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('Submit','Approve','RequestChanges')",
            name="ck_transitions_action",
        ),
        sa.CheckConstraint(
            "action != 'RequestChanges' OR "
            "(comment IS NOT NULL AND length(trim(comment)) > 0)",
            name="ck_transitions_request_changes_comment",
        ),
    )
    op.create_index(
        "ix_transitions_request_occurred",
        "change_request_transitions",
        ["change_request_id", "occurred_at"],
    )
    op.create_index(
        "ix_transitions_actor_action_request",
        "change_request_transitions",
        ["actor_id", "action", "change_request_id"],
    )


def downgrade() -> None:
    op.drop_table("change_request_transitions")
    op.drop_table("change_request_revisions")
    op.drop_table("user_role_assignments")
    op.drop_table("change_requests")
    op.drop_table("user_accounts")
