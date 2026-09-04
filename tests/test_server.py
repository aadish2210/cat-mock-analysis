import tempfile
import unittest
from pathlib import Path

from server import create_app
from storage import MockStore, ReviewStore


def sample_mock():
    return {
        "slug": "simcat-1",
        "title": "SimCAT 1",
        "imported_at": "2026-09-04T00:00:00+00:00",
        "attempted_at": None,
        "sections": [
            {
                "slug": "qa",
                "title": "Quantitative Ability",
                "questions": [
                    {
                        "id": "q1",
                        "number": 1,
                        "section_slug": "qa",
                        "difficulty": "A",
                        "question_type": "MCQ",
                        "topic": "Arithmetic",
                        "is_attempted": True,
                        "is_correct": True,
                        "score": 3,
                        "time_taken": 60,
                        "topper_p_value": 0.9,
                        "topper_avg_time_spend": 30,
                        "topper_attempt_percentage": 0.95,
                    },
                    {
                        "id": "q2",
                        "number": 2,
                        "section_slug": "qa",
                        "difficulty": "C",
                        "question_type": "MCQ",
                        "topic": "P&C",
                        "is_attempted": True,
                        "is_correct": False,
                        "score": -1,
                        "time_taken": 240,
                        "topper_p_value": 0.3,
                        "topper_avg_time_spend": 80,
                        "topper_attempt_percentage": 0.25,
                    },
                ],
            }
        ],
    }


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = MockStore(Path(self.directory.name) / "mocks.json")
        self.reviews = ReviewStore(Path(self.directory.name) / "reviews.json")
        self.app = create_app(self.store, review_store=self.reviews)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.directory.cleanup()

    def test_empty_summary_is_valid(self):
        response = self.client.get("/api/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["mock_count"], 0)

    def test_audit_and_divergence_use_stored_mock(self):
        self.store.upsert(sample_mock())
        audit = self.client.get("/api/mocks/simcat-1").get_json()
        divergence = self.client.get("/api/toppers/divergence").get_json()

        self.assertEqual(audit["potential"]["actual"], 2)
        self.assertEqual(len(divergence["topper_traps"]), 1)

    def test_coach_and_question_lookup_use_stored_mock(self):
        self.store.upsert(sample_mock())

        coach = self.client.get("/api/coach")
        question = self.client.get("/api/mocks/simcat-1/questions/q1")

        self.assertEqual(coach.status_code, 200)
        self.assertEqual(coach.get_json()["mock_count"], 1)
        self.assertEqual(question.status_code, 200)
        self.assertEqual(question.get_json()["topic"], "Arithmetic")

    def test_question_lookup_returns_not_found(self):
        self.store.upsert(sample_mock())
        response = self.client.get("/api/mocks/simcat-1/questions/missing")
        self.assertEqual(response.status_code, 404)

    def test_question_bank_is_compact_by_default(self):
        mock_data = sample_mock()
        mock_data["sections"][0]["questions"][0]["question_html"] = "<p>Large prompt</p>"
        mock_data["sections"][0]["questions"][0]["solution_html"] = "<p>Large solution</p>"
        self.store.upsert(mock_data)

        compact = self.client.get("/api/questions").get_json()[0]
        full = self.client.get("/api/questions?include_content=1").get_json()[0]

        self.assertEqual(compact["preview"], "Large prompt")
        self.assertNotIn("question_html", compact)
        self.assertNotIn("solution_html", compact)
        self.assertEqual(full["solution_html"], "<p>Large solution</p>")

    def test_review_round_trip_and_summary(self):
        self.store.upsert(sample_mock())

        saved = self.client.put(
            "/api/reviews/simcat-1/q1",
            json={"status": "learning", "note": "Rebuild the fast route."},
        )
        summary = self.client.get("/api/reviews").get_json()

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.get_json()["interval_days"], 3)
        self.assertEqual(summary["count"], 1)
        self.assertEqual(summary["counts"]["learning"], 1)
        self.assertEqual(summary["reviews"][0]["question"]["topic"], "Arithmetic")

    def test_review_rejects_unknown_question(self):
        response = self.client.put(
            "/api/reviews/missing/q1", json={"status": "again"}
        )
        self.assertEqual(response.status_code, 404)

    def test_simulator_rejects_invalid_time_cap(self):
        response = self.client.post("/api/simulator/run", json={"time_cap_seconds": 99})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()