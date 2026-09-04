import base64
import tempfile
import unittest
from pathlib import Path

from importer import extract_token, import_mock
from storage import MockStore


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        if url.endswith("/test/info"):
            return FakeResponse(
                {
                    "data": {
                        "title": "SimCAT Test 1",
                        "timeDurationInMilliSeconds": 7_200_000,
                        "instructions": [
                            {"instructions": _encoded("<p>Stay calm.</p>")}
                        ],
                        "groups": [{
                            "name": "Quantitative Ability",
                            "sections": [{
                                "_id": "qa-section",
                                "name": "Quantitative Ability",
                                "questions": [{
                                    "scoring": [{
                                        "question_id": "q9",
                                        "correct_answer": 3,
                                        "incorrect_answer": 0,
                                    }],
                                    "question_data": {
                                        "questions": [{
                                            "question_id": "q9",
                                            "type": "type-in-the-answer",
                                            "question": _encoded("<p>What is 6 x 7?</p>"),
                                            "options": [
                                                {
                                                    "option_id": "answer-1",
                                                    "text": _encoded("<p>Forty-two</p>"),
                                                    "is_correct": True,
                                                }
                                            ],
                                            "correct_answer": "42",
                                            "review": {"text": _encoded("<p>42</p>")},
                                            "area": "Quantitative Ability",
                                            "topic": "Arithmetic",
                                            "sub_topic": "Numbers",
                                            "response": {
                                                "status": "answered",
                                                "user_response": ["41"],
                                            },
                                        }]
                                    },
                                }],
                            }],
                        }],
                    }
                }
            )
        if url.endswith("/test-attempts/attempt-info"):
            return FakeResponse(
                {
                    "data": {
                        "groups": [{
                            "name": "Quantitative Ability",
                            "sections": [{
                                "name": "Quantitative Ability",
                                "questions": [{
                                    "_id": "q9",
                                    "status": "incorrect",
                                    "time_taken": 83_000,
                                    "advance_statistics": {
                                        "overall_statistics": {
                                            "p_value": 73,
                                            "average_time_taken": 45_000,
                                            "attempt_percentage": 81,
                                        },
                                        "toppers_statistics": {
                                            "p_value": 91,
                                            "average_time_taken": 31_000,
                                            "attempt_percentage": 96,
                                        },
                                    },
                                }],
                            }],
                        }],
                    }
                }
            )
        raise AssertionError(f"Unexpected IMS endpoint: {url}")


def _encoded(value):
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


class ImporterTests(unittest.TestCase):
    def test_extract_token_rejects_non_ims_shaped_url(self):
        with self.assertRaises(ValueError):
            extract_token("https://example.com/no-token")

    def test_import_normalizes_and_never_persists_token(self):
        token = "header.payload_signature"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mocks.json"
            session = FakeSession()
            mock = import_mock(
                f"https://test-player.imsindia.com/?token={token}",
                store=MockStore(path),
                session=session,
            )

            question = mock["sections"][0]["questions"][0]
            self.assertEqual(mock["slug"], "simcat-test-1")
            self.assertEqual(mock["duration_minutes"], 120)
            self.assertEqual(mock["instructions_html"], "<p>Stay calm.</p>")
            self.assertEqual(question["difficulty"], "A")
            self.assertEqual(question["score"], 0)
            self.assertTrue(question["is_attempted"])
            self.assertFalse(question["is_correct"])
            self.assertEqual(question["time_taken"], 83)
            self.assertEqual(question["p_value"], 0.73)
            self.assertEqual(question["topper_p_value"], 0.91)
            self.assertEqual(question["topper_avg_time_spend"], 31)
            self.assertEqual(question["question_html"], "<p>What is 6 x 7?</p>")
            self.assertEqual(question["solution_html"], "<p>42</p>")
            self.assertEqual(question["options"][0]["html"], "<p>Forty-two</p>")
            self.assertEqual(
                [url.rsplit("/", 1)[-1] for url in session.urls],
                ["info", "attempt-info"],
            )
            self.assertNotIn(token, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()