import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from storage import ReviewStore


class ReviewStoreTests(unittest.TestCase):
    def test_review_status_sets_interval_and_increments_count(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.json")
            now = datetime(2026, 9, 4, tzinfo=UTC)

            first = store.update("mock-1", "q1", status="learning", note="Redo algebra", now=now)
            second = store.update(
                "mock-1",
                "q1",
                status="mastered",
                note="Stable now",
                now=now + timedelta(days=3),
            )

            self.assertEqual(first["next_review_at"], "2026-09-07T00:00:00+00:00")
            self.assertEqual(second["review_count"], 2)
            self.assertEqual(second["next_review_at"], "2026-09-21T00:00:00+00:00")
            self.assertEqual(store.get("mock-1", "q1")["note"], "Stable now")

    def test_due_filters_future_reviews(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.json")
            now = datetime(2026, 9, 4, tzinfo=UTC)
            store.update("mock-1", "q1", status="again", now=now)

            self.assertEqual(store.due(now), [])
            self.assertEqual(len(store.due(now + timedelta(days=1))), 1)

    def test_rejects_invalid_status(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.json")
            with self.assertRaises(ValueError):
                store.update("mock-1", "q1", status="later")


if __name__ == "__main__":
    unittest.main()