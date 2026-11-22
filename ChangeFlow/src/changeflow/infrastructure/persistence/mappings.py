from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserAccountModel(Base):
    __tablename__ = "user_accounts"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserRoleAssignmentModel(Base):
    __tablename__ = "user_role_assignments"

    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)


class ChangeRequestModel(Base):
    __tablename__ = "change_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    requester_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("user_accounts.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    latest_reviewed_revision_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": lambda current: uuid4(),
    }
    __table_args__ = (
        Index("ix_change_requests_status_requester", "status", "requester_id"),
        CheckConstraint(
            "status IN ('Draft','PendingReview','Approved','ChangesRequested')",
            name="ck_change_requests_status",
        ),
    )


class ChangeRequestRevisionModel(Base):
    __tablename__ = "change_request_revisions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_by: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("user_accounts.id"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "change_request_id",
            "revision_number",
            name="uq_revision_request_number",
        ),
    )


class ChangeRequestTransitionModel(Base):
    __tablename__ = "change_request_transitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    change_request_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("change_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("user_accounts.id"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("change_request_revisions.id"),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "ix_transitions_request_occurred",
            "change_request_id",
            "occurred_at",
        ),
        Index(
            "ix_transitions_actor_action_request",
            "actor_id",
            "action",
            "change_request_id",
        ),
        CheckConstraint(
            "action IN ('Submit','Approve','RequestChanges')",
            name="ck_transitions_action",
        ),
        CheckConstraint(
            "action != 'RequestChanges' OR (comment IS NOT NULL AND length(trim(comment)) > 0)",
            name="ck_transitions_request_changes_comment",
        ),
    )


def utcnow() -> datetime:
    return datetime.now(UTC)
