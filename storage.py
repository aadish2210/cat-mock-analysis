from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_STORE_PATH = Path(__file__).resolve().parent / "data" / "mocks.json"
DEFAULT_REVIEW_PATH = Path(__file__).resolve().parent / "data" / "review_state.json"


class MockStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_STORE_PATH
        self._lock = threading.RLock()

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self.path.exists():
                return []
            with self.path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or not isinstance(payload.get("mocks"), list):
                raise ValueError(f"Invalid mock store: {self.path}")
            return payload["mocks"]

    def get(self, slug: str) -> dict[str, Any] | None:
        return next((mock for mock in self.all() if mock.get("slug") == slug), None)

    def upsert(self, mock: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            mocks = self.all()
            mocks = [stored for stored in mocks if stored.get("slug") != mock.get("slug")]
            mocks.append(mock)
            mocks.sort(key=lambda item: (item.get("attempted_at") or item.get("imported_at") or ""))
            self._write({"version": 1, "mocks": mocks})
        return mock

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temporary_path = Path(handle.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()


class ReviewStore:
    INTERVALS = {"again": 1, "learning": 3, "mastered": 14}

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_REVIEW_PATH
        self._lock = threading.RLock()

    def all(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self.path.exists():
                return []
            with self.path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict) or not isinstance(payload.get("reviews"), dict):
                raise ValueError(f"Invalid review store: {self.path}")
            return list(payload["reviews"].values())

    def get(self, mock_slug: str, question_id: str) -> dict[str, Any] | None:
        key = self._key(mock_slug, question_id)
        return next((item for item in self.all() if item.get("key") == key), None)

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
        key = self._key(mock_slug, question_id)
        with self._lock:
            reviews = {item["key"]: item for item in self.all()}
            existing = reviews.get(key, {})
            interval_days = self.INTERVALS[status]
            review = {
                "key": key,
                "mock_slug": mock_slug,
                "question_id": question_id,
                "status": status,
                "note": note.strip(),
                "review_count": int(existing.get("review_count", 0)) + 1,
                "last_reviewed_at": current_time.isoformat(),
                "next_review_at": (current_time + timedelta(days=interval_days)).isoformat(),
                "interval_days": interval_days,
            }
            reviews[key] = review
            self._write({"version": 1, "reviews": reviews})
        return review

    def due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current_time = now or datetime.now(UTC)
        return sorted(
            [
                review
                for review in self.all()
                if datetime.fromisoformat(review["next_review_at"]) <= current_time
            ],
            key=lambda review: review["next_review_at"],
        )

    @staticmethod
    def _key(mock_slug: str, question_id: str) -> str:
        return f"{mock_slug}:{question_id}"

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                temporary_path = Path(handle.name)
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()