from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests


class SupabaseStorageError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class SupabaseRestClient:
    def __init__(
        self,
        url: str,
        publishable_key: str,
        access_token: str,
        session: requests.Session | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.publishable_key = publishable_key
        self.access_token = access_token
        self.session = session or requests.Session()

    def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = self.session.request(
                method,
                f"{self.url}/rest/v1/{table}",
                params=params,
                json=payload,
                headers=headers,
                timeout=45,
            )
        except requests.RequestException as error:
            raise SupabaseStorageError("Cloud storage is temporarily unavailable.") from error
        if not response.ok:
            try:
                detail = response.json().get("message")
            except (ValueError, AttributeError):
                detail = None
            if response.status_code == 404 or "schema cache" in str(detail).casefold():
                message = "Supabase tables are not provisioned. Run the bundled schema migration."
            elif response.status_code in {401, 403}:
                message = "Cloud storage denied this session. Sign in again."
            else:
                message = detail or "Cloud storage rejected the request."
            raise SupabaseStorageError(message, response.status_code)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()


class SupabaseMockStore:
    def __init__(self, client: SupabaseRestClient, user_id: str) -> None:
        self.client = client
        self.user_id = user_id

    def all(self) -> list[dict[str, Any]]:
        rows = self.client.request(
            "GET",
            "mock_attempts",
            params={
                "select": "payload",
                "user_id": f"eq.{self.user_id}",
                "order": "imported_at.asc",
            },
        )
        return [row["payload"] for row in rows or [] if isinstance(row.get("payload"), dict)]

    def get(self, slug: str) -> dict[str, Any] | None:
        rows = self.client.request(
            "GET",
            "mock_attempts",
            params={
                "select": "payload",
                "user_id": f"eq.{self.user_id}",
                "slug": f"eq.{slug}",
                "limit": "1",
            },
        )
        return rows[0]["payload"] if rows else None

    def upsert(self, mock: dict[str, Any]) -> dict[str, Any]:
        self.client.request(
            "POST",
            "mock_attempts",
            params={"on_conflict": "user_id,slug"},
            payload={
                "user_id": self.user_id,
                "slug": mock.get("slug"),
                "title": mock.get("title"),
                "attempted_at": mock.get("attempted_at"),
                "imported_at": mock.get("imported_at"),
                "payload": mock,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )
        return mock


class SupabaseReviewStore:
    INTERVALS = {"again": 1, "learning": 3, "mastered": 14}

    def __init__(self, client: SupabaseRestClient, user_id: str) -> None:
        self.client = client
        self.user_id = user_id

    @staticmethod
    def _key(mock_slug: str, question_id: str) -> str:
        return f"{mock_slug}:{question_id}"

    def all(self) -> list[dict[str, Any]]:
        rows = self.client.request(
            "GET",
            "question_reviews",
            params={
                "select": "mock_slug,question_id,status,note,review_count,last_reviewed_at,next_review_at,interval_days",
                "user_id": f"eq.{self.user_id}",
                "order": "next_review_at.asc",
            },
        )
        return [
            {**row, "key": self._key(str(row["mock_slug"]), str(row["question_id"]))}
            for row in rows or []
        ]

    def get(self, mock_slug: str, question_id: str) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self.all()
                if item["mock_slug"] == mock_slug and item["question_id"] == question_id
            ),
            None,
        )

    def update(
        self,
        mock_slug: str,
        question_id: str,
        *,
        status: str,
        note: str = "",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if status not in self.INTERVALS:
            raise ValueError("status must be again, learning, or mastered")
        if len(note) > 2000:
            raise ValueError("note must be 2000 characters or fewer")
        current_time = now or datetime.now(UTC)
        existing = self.get(mock_slug, question_id) or {}
        interval_days = self.INTERVALS[status]
        row = {
            "user_id": self.user_id,
            "mock_slug": mock_slug,
            "question_id": question_id,
            "status": status,
            "note": note.strip(),
            "review_count": int(existing.get("review_count", 0)) + 1,
            "last_reviewed_at": current_time.isoformat(),
            "next_review_at": (current_time + timedelta(days=interval_days)).isoformat(),
            "interval_days": interval_days,
            "updated_at": current_time.isoformat(),
        }
        self.client.request(
            "POST",
            "question_reviews",
            params={"on_conflict": "user_id,mock_slug,question_id"},
            payload=row,
            prefer="resolution=merge-duplicates,return=minimal",
        )
        return {**row, "key": self._key(mock_slug, question_id)}

    def due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current_time = now or datetime.now(UTC)
        return [
            item
            for item in self.all()
            if datetime.fromisoformat(item["next_review_at"]) <= current_time
        ]


class SupabaseProfileStore:
    def __init__(self, client: SupabaseRestClient, user_id: str) -> None:
        self.client = client
        self.user_id = user_id

    def get(self) -> dict[str, Any] | None:
        rows = self.client.request(
            "GET",
            "profiles",
            params={
                "select": "id,display_name,avatar_url,timezone,created_at,updated_at",
                "id": f"eq.{self.user_id}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def update(self, display_name: str, timezone: str = "Asia/Kolkata") -> dict[str, Any]:
        cleaned_name = display_name.strip()
        if not 1 <= len(cleaned_name) <= 80:
            raise ValueError("display_name must be between 1 and 80 characters")
        row = {
            "id": self.user_id,
            "display_name": cleaned_name,
            "timezone": timezone.strip() or "Asia/Kolkata",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = self.client.request(
            "POST",
            "profiles",
            params={"on_conflict": "id"},
            payload=row,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return result[0] if result else row