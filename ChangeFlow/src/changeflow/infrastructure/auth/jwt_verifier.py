from typing import Any, Protocol

import jwt
from jwt import PyJWKClient

from changeflow.application.errors import AuthenticationError
from changeflow.infrastructure.config import Settings


class SigningKeyResolver(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class JwtVerifier:
    def __init__(
        self,
        settings: Settings,
        signing_key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        self._settings = settings
        self._signing_key_resolver = signing_key_resolver or PyJWKClient(
            settings.jwt_jwks_url
        )

    def verify(self, token: str) -> str:
        try:
            signing_key = self._signing_key_resolver.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self._settings.jwt_algorithm],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except (jwt.PyJWTError, ValueError, AttributeError) as exc:
            raise AuthenticationError("caller credentials are invalid") from exc
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("caller credentials are invalid")
        return subject
