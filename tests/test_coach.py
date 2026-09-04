import unittest

from reporting import build_coach_report


def question(
    question_id,
    *,
    section="qa",
    topic="Arithmetic",
    difficulty="B",
    attempted=True,
    correct=True,
    score=3,
    time=90,
    topper_time=60,
    topper_accuracy=0.75,
):
    return {
        "id": question_id,
        "number": question_id,
        "section_slug": section,
        "topic": topic,
        "difficulty": difficulty,
        "question_type": "MCQ",
        "is_attempted": attempted,
        "is_correct": correct,
        "score": score,
        "time_taken": time,
        "topper_p_value": topper_accuracy,
        "topper_avg_time_spend": topper_time,
        "topper_attempt_percentage": 0.8,
    }


def mock(slug, questions):
    return {
        "slug": slug,
        "title": slug,
        "imported_at": f"2026-01-0{slug[-1]}T00:00:00Z",
        "sections": [{"slug": "qa", "title": "QA", "questions": questions}],
    }


class CoachReportTests(unittest.TestCase):
    def test_prioritizes_consensus_misses_and_builds_bounded_index(self):
        mocks = [
            mock(
                "mock-1",
                [
                    question(1),
                    question(2, difficulty="A", attempted=False, correct=False, score=0, topper_accuracy=0.9),
                    question(3, difficulty="C", correct=False, score=-1, time=240, topper_accuracy=0.3),
                ],
            ),
            mock(
                "mock-2",
                [
                    question(4),
                    question(5, correct=True, time=210, topper_time=60),
                    question(6, correct=False, score=-1, topper_accuracy=0.5),
                ],
            ),
        ]

        report = build_coach_report(mocks)

        self.assertEqual(report["mock_count"], 2)
        self.assertEqual(report["practice_queue"][0]["reason"], "Consensus miss")
        self.assertTrue(any(item["kind"] == "banker_conversion" for item in report["priorities"]))
        self.assertEqual(sum(band["count"] for band in report["pace_bands"]), 5)
        self.assertGreaterEqual(report["scorecard"]["discipline_index"], 0)
        self.assertLessEqual(report["scorecard"]["discipline_index"], 100)

    def test_empty_report_is_stable(self):
        report = build_coach_report([])
        self.assertEqual(report["mock_count"], 0)
        self.assertEqual(report["priorities"], [])

    def test_trajectory_uses_natural_mock_order_not_import_order(self):
        mocks = [
            {**mock("mock-11", [question(11)]), "imported_at": "2026-01-01T00:00:00Z"},
            {**mock("mock-2", [question(2)]), "imported_at": "2026-01-03T00:00:00Z"},
            {**mock("mock-9", [question(9)]), "imported_at": "2026-01-02T00:00:00Z"},
        ]

        report = build_coach_report(mocks)

        self.assertEqual(
            [item["title"] for item in report["trajectory"]],
            ["mock-2", "mock-9", "mock-11"],
        )


if __name__ == "__main__":
    unittest.main()