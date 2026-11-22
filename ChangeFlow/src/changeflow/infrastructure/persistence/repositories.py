from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from changeflow.application.errors import ConcurrencyConflictError
from changeflow.domain.change_requests.entities import (
    ChangeRequest,
    ChangeRequestRevision,
    ChangeRequestTransition,
)
from changeflow.domain.change_requests.enums import (
    ChangeRequestAction,
    ChangeRequestStatus,
)
from changeflow.domain.change_requests.values import ChangeRequestContent as ContentValue

from .mappings import (
    ChangeRequestModel,
    ChangeRequestRevisionModel,
    ChangeRequestTransitionModel,
)


class SqlAlchemyChangeRequestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, request_id: UUID) -> ChangeRequest | None:
        model = self._session.get(ChangeRequestModel, request_id)
        return self._to_domain(model) if model else None

    def list_all(self) -> list[ChangeRequest]:
        models: Sequence[ChangeRequestModel] = self._session.scalars(
            select(ChangeRequestModel).order_by(ChangeRequestModel.created_at)
        ).all()
        return [self._to_domain(model) for model in models]

    def save(self, request: ChangeRequest) -> ChangeRequest:
        model = self._session.get(ChangeRequestModel, request.id)
        if model is None:
            model = ChangeRequestModel(
                id=request.id,
                requester_id=request.requester_id,
                title=request.content.title,
                description=request.content.description,
                reason=request.content.reason,
                status=request.status.value,
                latest_reviewed_revision_id=request.latest_reviewed_revision_id,
                created_at=request.created_at,
                updated_at=request.updated_at,
            )
            self._session.add(model)
        else:
            model.title = request.content.title
            model.description = request.content.description
            model.reason = request.content.reason
            model.status = request.status.value
            model.latest_reviewed_revision_id = request.latest_reviewed_revision_id
            model.updated_at = request.updated_at
        try:
            self._session.flush()
        except StaleDataError as exc:
            self._session.rollback()
            current_version = self._session.scalar(
                select(ChangeRequestModel.version).where(
                    ChangeRequestModel.id == request.id
                )
            )
            raise ConcurrencyConflictError(
                "the request was changed by another operation",
                current_version=current_version,
            ) from exc
        self._session.refresh(model)
        request.version = model.version
        return request

    def get_revision(self, revision_id: UUID) -> ChangeRequestRevision | None:
        model = self._session.get(ChangeRequestRevisionModel, revision_id)
        return self._revision_to_domain(model) if model else None

    def get_latest_submitted_revision(
        self, request_id: UUID
    ) -> ChangeRequestRevision | None:
        model = self._session.scalar(
            select(ChangeRequestRevisionModel)
            .where(ChangeRequestRevisionModel.change_request_id == request_id)
            .order_by(ChangeRequestRevisionModel.revision_number.desc())
            .limit(1)
        )
        return self._revision_to_domain(model) if model else None

    def next_revision_number(self, request_id: UUID) -> int:
        current = self._session.scalar(
            select(func.max(ChangeRequestRevisionModel.revision_number)).where(
                ChangeRequestRevisionModel.change_request_id == request_id
            )
        )
        return int(current or 0) + 1

    def add_revision(self, revision: ChangeRequestRevision) -> None:
        self._session.add(
            ChangeRequestRevisionModel(
                id=revision.id,
                change_request_id=revision.change_request_id,
                revision_number=revision.revision_number,
                title=revision.content.title,
                description=revision.content.description,
                reason=revision.content.reason,
                submitted_at=revision.submitted_at,
                submitted_by=revision.submitted_by,
            )
        )
        self._session.flush()

    def add_transition(self, transition: ChangeRequestTransition) -> None:
        self._session.add(
            ChangeRequestTransitionModel(
                id=transition.id,
                change_request_id=transition.change_request_id,
                actor_id=transition.actor_id,
                action=transition.action.value,
                from_status=transition.from_status.value,
                to_status=transition.to_status.value,
                comment=transition.comment,
                reviewed_revision_id=transition.reviewed_revision_id,
                occurred_at=transition.occurred_at,
            )
        )
        self._session.flush()

    def list_transitions(self, request_id: UUID) -> list[ChangeRequestTransition]:
        models: Sequence[ChangeRequestTransitionModel] = self._session.scalars(
            select(ChangeRequestTransitionModel)
            .where(ChangeRequestTransitionModel.change_request_id == request_id)
            .order_by(ChangeRequestTransitionModel.occurred_at)
        ).all()
        return [
            ChangeRequestTransition(
                id=model.id,
                change_request_id=model.change_request_id,
                actor_id=model.actor_id,
                action=ChangeRequestAction(model.action),
                from_status=ChangeRequestStatus(model.from_status),
                to_status=ChangeRequestStatus(model.to_status),
                occurred_at=model.occurred_at,
                comment=model.comment,
                reviewed_revision_id=model.reviewed_revision_id,
            )
            for model in models
        ]

    def _to_domain(self, model: ChangeRequestModel) -> ChangeRequest:
        reviewers = self._session.scalars(
            select(ChangeRequestTransitionModel.actor_id)
            .where(
                ChangeRequestTransitionModel.change_request_id == model.id,
                ChangeRequestTransitionModel.action.in_(
                    [ChangeRequestAction.APPROVE.value, ChangeRequestAction.REQUEST_CHANGES.value]
                ),
            )
            .distinct()
        ).all()
        return ChangeRequest(
            id=model.id,
            requester_id=model.requester_id,
            content=ContentValue(
                title=model.title,
                description=model.description,
                reason=model.reason,
            ),
            status=ChangeRequestStatus(model.status),
            version=model.version,
            latest_reviewed_revision_id=model.latest_reviewed_revision_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            prior_reviewer_ids=set(reviewers),
        )

    @staticmethod
    def _revision_to_domain(
        model: ChangeRequestRevisionModel,
    ) -> ChangeRequestRevision:
        return ChangeRequestRevision(
            id=model.id,
            change_request_id=model.change_request_id,
            revision_number=model.revision_number,
            content=ContentValue(
                title=model.title,
                description=model.description,
                reason=model.reason,
            ),
            submitted_at=model.submitted_at,
            submitted_by=model.submitted_by,
        )
