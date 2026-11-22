from dataclasses import dataclass
from typing import Protocol

from changeflow.domain.change_requests.enums import Role


@dataclass(frozen=True)
class CurrentUser:
    id: str
    roles: frozenset[Role]


class CurrentUserRoleStore(Protocol):
    def get(self, user_id: str) -> CurrentUser | None:
        """Return the active user and current roles, if any."""
