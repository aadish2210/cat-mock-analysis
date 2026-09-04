from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests


class AuthError(RuntimeError):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class UserIdentity:
    id: str
    email: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return str(
            self.metadata.get("full_name")
            or self.metadata.get("name")
            or self.email.split("@", 1)[0]
            or "Candidate"
        )

    def public_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "avatar_url": self.metadata.get("avatar_url"),
        }


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("Sign in to continue.")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token.strip():
        raise AuthError("A valid bearer token is required.")
    return token.strip()


class SupabaseAuthVerifier:
    def __init__(
        self,
        url: str,
        publishable_key: str,
        session: requests.Session | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.publishable_key = publishable_key
        self.session = session or requests.Session()

    def verify(self, access_token: str) -> UserIdentity:
        try:
            response = self.session.get(
                f"{self.url}/auth/v1/user",
                headers={
                    "apikey": self.publishable_key,
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
        except requests.RequestException as error:
            raise AuthError("Authentication service is temporarily unavailable.", 503) from error
        if response.status_code in {401, 403}:
            raise AuthError("Your session has expired. Sign in again.")
        if not response.ok:
            raise AuthError("Authentication service rejected the request.", 503)
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("id"):
            raise AuthError("Authentication service returned an invalid user.", 503)
        metadata = payload.get("user_metadata")
        return UserIdentity(
            id=str(payload["id"]),
            email=str(payload.get("email") or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
        )