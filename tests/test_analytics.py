import unittest

from analytics import classify_question, potential_score, simulate_questions


class ClassificationTests(unittest.TestCase):
    def test_low_topper_consensus_overrides_easy_population_signal(self):
        self.assertEqual(classify_question(0.72, 0.42, 0.31), "C")

    def test_topper_accuracy_can_identify_a_banker(self):
        self.assertEqual(classify_question(0.28, 0.90, 0.70), "A")


class PotentialScoreTests(unittest.TestCase):
    def test_uses_actual_tita_penalty_for_recovery(self):
        result = potential_score(
            [
                {"difficulty": "A", "is_attempted": True, "is_correct": False, "score": 0},
                {"difficulty": "A", "is_attempted": True, "is_correct": False, "score": -1},
                {"difficulty": "A", "is_attempted": False, "is_correct": False, "score": 0},
                {"difficulty": "C", "is_attempted": True, "is_correct": False, "score": -1},
            ]
        )

        self.assertEqual(result["actual"], -2)
        self.assertEqual(result["incorrect_type_a_gain"], 7)
        self.assertEqual(result["potential"], 9)


class SimulatorTests(unittest.TestCase):
    def test_applies_capacity_per_section(self):
        result = simulate_questions(
            [
                {
                    "id": 1,
                    "section_slug": "qa",
                    "difficulty": "C",
                    "is_attempted": True,
                    "is_correct": False,
                    "score": -1,
                    "time_taken": 300,
                    "topic": "P&C",
                },
                {
                    "id": 2,
                    "section_slug": "qa",
                    "difficulty": "A",
                    "is_attempted": False,
                    "is_correct": False,
                    "score": 0,
                    "time_taken": 0,
                    "topic": "Arithmetic",
                },
            ],
            time_cap_seconds=120,
            type_c_immunity=True,
            type_a_conversion_rate=1,
        )

        self.assertEqual(result["freed_minutes"], 5)
        self.assertEqual(result["penalties_saved"], 1)
        self.assertEqual(result["conversion_gain"], 3)
        self.assertEqual(result["simulated_score"], 3)


if __name__ == "__main__":
    unittest.main()