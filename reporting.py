from __future__ import annotations

import re
from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Any, Iterable

from analytics import potential_score, simulate_questions


def ordered_mocks(mocks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    def order_key(mock: dict[str, Any]):
        attempted_at = str(mock.get("attempted_at") or "")
        if attempted_at:
            return (0, attempted_at, 0, str(mock.get("title") or ""))
        title = str(mock.get("title") or "")
        numbered = re.search(r"\b(?:simcat|mock)\s*[-#:]?\s*(\d+)\b", title, re.IGNORECASE)
        if numbered:
            return (1, "", int(numbered.group(1)), title.casefold())
        return (2, str(mock.get("imported_at") or ""), 0, title.casefold())

    return sorted(mocks, key=order_key)


def flatten_questions(mock: dict[str, Any]) -> list[dict[str, Any]]:
    questions = []
    for section in mock.get("sections", []):
        for question in section.get("questions", []):
            questions.append(
                {
                    **question,
                    "section_slug": section.get("slug", question.get("section_slug")),
                    "section_title": section.get("title"),
                    "mock_slug": mock.get("slug"),
                    "mock_title": mock.get("title"),
                }
            )
    return questions


def _accuracy(questions: Iterable[dict[str, Any]]) -> float:
    attempted = [question for question in questions if question.get("is_attempted")]
    if not attempted:
        return 0.0
    return round(
        sum(1 for question in attempted if question.get("is_correct")) / len(attempted) * 100,
        1,
    )


def _question_ref(question: dict[str, Any]) -> dict[str, Any]:
    return {
        key: question.get(key)
        for key in (
            "id",
            "number",
            "mock_slug",
            "mock_title",
            "section_slug",
            "section_title",
            "topic",
            "sub_topic",
            "difficulty",
            "question_type",
            "is_attempted",
            "is_correct",
            "score",
            "time_taken",
            "p_value",
            "topper_p_value",
            "topper_avg_time_spend",
            "topper_attempt_percentage",
        )
    }


def build_summary(mocks: list[dict[str, Any]]) -> dict[str, Any]:
    mocks = ordered_mocks(mocks)
    trajectory = []
    section_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_questions = []

    for mock in mocks:
        questions = flatten_questions(mock)
        all_questions.extend(questions)
        potential = potential_score(questions)
        trajectory.append(
            {
                "slug": mock.get("slug"),
                "title": mock.get("title"),
                "date": mock.get("attempted_at") or mock.get("imported_at"),
                "score": potential["actual"],
                "potential": potential["potential"],
                "accuracy": _accuracy(questions),
                "attempted": sum(1 for question in questions if question.get("is_attempted")),
                "question_count": len(questions),
            }
        )
        for question in questions:
            section_groups[str(question.get("section_slug"))].append(question)

    section_averages = []
    for section_slug, questions in section_groups.items():
        scores_by_mock = []
        for mock in mocks:
            section_questions = [
                question
                for question in flatten_questions(mock)
                if question.get("section_slug") == section_slug
            ]
            if section_questions:
                scores_by_mock.append(sum(float(question.get("score") or 0) for question in section_questions))
        section_averages.append(
            {
                "section": section_slug,
                "average_score": round(mean(scores_by_mock), 1) if scores_by_mock else 0,
                "accuracy": _accuracy(questions),
                "average_time_seconds": round(
                    mean(float(question.get("time_taken") or 0) for question in questions), 1
                ),
            }
        )

    time_sinks = [
        question
        for question in all_questions
        if float(question.get("time_taken") or 0) > 180 and float(question.get("score") or 0) <= 0
    ]
    total_score = sum(float(question.get("score") or 0) for question in all_questions)

    return {
        "mock_count": len(mocks),
        "question_count": len(all_questions),
        "total_score": round(total_score, 1),
        "average_score": round(total_score / len(mocks), 1) if mocks else 0,
        "average_accuracy": _accuracy(all_questions),
        "time_sinks": {
            "count": len(time_sinks),
            "minutes": round(sum(float(question.get("time_taken") or 0) for question in time_sinks) / 60, 1),
        },
        "trajectory": trajectory[-16:],
        "section_averages": sorted(section_averages, key=lambda item: item["section"]),
    }


def build_mock_audit(mock: dict[str, Any]) -> dict[str, Any]:
    questions = flatten_questions(mock)
    sections = []
    trade_offs = []

    for section in mock.get("sections", []):
        section_questions = [
            question for question in questions if question.get("section_slug") == section.get("slug")
        ]
        time_sinks = [
            question
            for question in section_questions
            if float(question.get("time_taken") or 0) > 180
            and float(question.get("score") or 0) <= 0
        ]
        starved = [
            question
            for question in section_questions
            if question.get("difficulty") == "A"
            and (not question.get("is_attempted") or not question.get("is_correct"))
        ]
        score = sum(float(question.get("score") or 0) for question in section_questions)
        sections.append(
            {
                "slug": section.get("slug"),
                "title": section.get("title"),
                "score": round(score, 1),
                "accuracy": _accuracy(section_questions),
                "attempted": sum(1 for question in section_questions if question.get("is_attempted")),
                "question_count": len(section_questions),
                "time_minutes": round(
                    sum(float(question.get("time_taken") or 0) for question in section_questions) / 60,
                    1,
                ),
            }
        )
        if time_sinks or starved:
            trade_offs.append(
                {
                    "section": section.get("slug"),
                    "section_title": section.get("title"),
                    "time_sinks": [_question_ref(question) for question in time_sinks],
                    "starved_freebies": [_question_ref(question) for question in starved],
                    "recoverable_minutes": round(
                        sum(float(question.get("time_taken") or 0) - 180 for question in time_sinks) / 60,
                        1,
                    ),
                    "available_marks": len(starved) * 3,
                }
            )

    return {
        "mock": {key: mock.get(key) for key in ("slug", "title", "attempted_at", "imported_at")},
        "potential": potential_score(questions),
        "sections": sections,
        "trade_offs": trade_offs,
        "questions": questions,
    }


def build_divergence(mocks: list[dict[str, Any]]) -> dict[str, Any]:
    questions = [question for mock in mocks for question in flatten_questions(mock)]
    topper_traps = []
    speed_gaps = []
    freebies_missed = []
    topic_excess: dict[str, dict[str, float]] = defaultdict(
        lambda: {"excess_seconds": 0.0, "questions": 0.0}
    )

    for question in questions:
        topper_accuracy = question.get("topper_p_value")
        topper_attempt = question.get("topper_attempt_percentage")
        topper_time = float(question.get("topper_avg_time_spend") or 0)
        candidate_time = float(question.get("time_taken") or 0)
        attempted_wrong = question.get("is_attempted") and not question.get("is_correct")

        if attempted_wrong and (
            (topper_accuracy is not None and topper_accuracy < 0.50)
            or (topper_attempt is not None and topper_attempt < 0.40)
        ):
            topper_traps.append(_question_ref(question))
        if question.get("is_correct") and topper_time > 0 and candidate_time > topper_time * 2.5:
            speed_gaps.append(
                {**_question_ref(question), "speed_multiple": round(candidate_time / topper_time, 1)}
            )
        if topper_accuracy is not None and topper_accuracy > 0.80 and (
            not question.get("is_attempted") or not question.get("is_correct")
        ):
            freebies_missed.append(_question_ref(question))
        if question.get("is_attempted") and topper_time > 0 and candidate_time > topper_time:
            topic = str(question.get("topic") or "Unclassified")
            topic_excess[topic]["excess_seconds"] += candidate_time - topper_time
            topic_excess[topic]["questions"] += 1

    topic_leaderboard = [
        {
            "topic": topic,
            "excess_minutes": round(values["excess_seconds"] / 60, 1),
            "questions": int(values["questions"]),
        }
        for topic, values in topic_excess.items()
    ]
    topic_leaderboard.sort(key=lambda item: item["excess_minutes"], reverse=True)

    return {
        "topper_traps": topper_traps,
        "speed_gaps": speed_gaps,
        "consensus_freebies_missed": freebies_missed,
        "topic_excess_minutes": topic_leaderboard,
    }


def build_section_report(mocks: list[dict[str, Any]], section_slug: str) -> dict[str, Any]:
    questions = [
        question
        for mock in mocks
        for question in flatten_questions(mock)
        if question.get("section_slug") == section_slug
    ]
    matrices = {
        "bankers": [question for question in questions if question.get("difficulty") == "A"],
        "grinders": [question for question in questions if question.get("difficulty") == "B"],
        "traps": [question for question in questions if question.get("difficulty") == "C"],
    }
    topic_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        topic_groups[str(question.get("topic") or "Unclassified")].append(question)

    topics = []
    for topic, topic_questions in topic_groups.items():
        attempted = [question for question in topic_questions if question.get("is_attempted")]
        topics.append(
            {
                "topic": topic,
                "questions": len(topic_questions),
                "attempted": len(attempted),
                "accuracy": _accuracy(topic_questions),
                "average_time_seconds": round(
                    mean(float(question.get("time_taken") or 0) for question in attempted), 1
                )
                if attempted
                else 0,
                "topper_time_seconds": round(
                    mean(
                        float(question.get("topper_avg_time_spend") or 0)
                        for question in topic_questions
                        if float(question.get("topper_avg_time_spend") or 0) > 0
                    ),
                    1,
                )
                if any(float(question.get("topper_avg_time_spend") or 0) > 0 for question in topic_questions)
                else 0,
            }
        )
    topics.sort(key=lambda item: (item["accuracy"], -item["questions"]))

    return {
        "section": section_slug,
        "question_count": len(questions),
        "score": round(sum(float(question.get("score") or 0) for question in questions), 1),
        "accuracy": _accuracy(questions),
        "matrix": {
            name: {
                "count": len(items),
                "attempted": sum(1 for item in items if item.get("is_attempted")),
                "accuracy": _accuracy(items),
            }
            for name, items in matrices.items()
        },
        "pacing": {
            "average_seconds": round(
                mean(float(question.get("time_taken") or 0) for question in questions), 1
            )
            if questions
            else 0,
            "time_sink_count": sum(
                1
                for question in questions
                if float(question.get("time_taken") or 0) > 180
                and float(question.get("score") or 0) <= 0
            ),
        },
        "topics": topics,
    }


def build_simulation(
    mocks: list[dict[str, Any]],
    *,
    mock_slug: str | None,
    time_cap_seconds: int,
    topic_blacklists: list[str],
    type_c_immunity: bool,
    type_a_conversion_rate: float,
) -> dict[str, Any]:
    if time_cap_seconds not in {120, 150, 180}:
        raise ValueError("time_cap_seconds must be 120, 150, or 180")
    if not 0 <= type_a_conversion_rate <= 1:
        raise ValueError("type_a_conversion_rate must be between 0 and 1")

    selected_mocks = [mock for mock in mocks if not mock_slug or mock.get("slug") == mock_slug]
    results = []
    for mock in selected_mocks:
        result = simulate_questions(
            flatten_questions(mock),
            time_cap_seconds=time_cap_seconds,
            topic_blacklists=topic_blacklists,
            type_c_immunity=type_c_immunity,
            type_a_conversion_rate=type_a_conversion_rate,
        )
        results.append({"slug": mock.get("slug"), "title": mock.get("title"), **result})

    return {
        "settings": {
            "mock_slug": mock_slug,
            "time_cap_seconds": time_cap_seconds,
            "topic_blacklists": topic_blacklists,
            "type_c_immunity": type_c_immunity,
            "type_a_conversion_rate": type_a_conversion_rate,
        },
        "actual_score": round(sum(result["actual_score"] for result in results), 1),
        "simulated_score": round(sum(result["simulated_score"] for result in results), 1),
        "freed_minutes": round(sum(result["freed_minutes"] for result in results), 1),
        "penalties_saved": round(sum(result["penalties_saved"] for result in results), 1),
        "conversion_gain": round(sum(result["conversion_gain"] for result in results), 1),
        "mocks": results,
    }


def _percentile(values: Iterable[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _average(values: Iterable[float]) -> float:
    rows = list(values)
    return round(mean(rows), 1) if rows else 0.0


def _topic_key(question: dict[str, Any]) -> tuple[str, str]:
    return (
        str(question.get("section_slug") or "unknown"),
        str(question.get("topic") or "Unclassified"),
    )


def build_coach_report(mocks: list[dict[str, Any]]) -> dict[str, Any]:
    mocks = ordered_mocks(mocks)
    if not mocks:
        return {
            "mock_count": 0,
            "scorecard": {},
            "trajectory": [],
            "sections": [],
            "error_lenses": [],
            "pace_bands": [],
            "topic_matrix": [],
            "priorities": [],
            "protocol": [],
            "practice_queue": [],
        }

    snapshots = []
    all_questions = []
    for mock in mocks:
        questions = flatten_questions(mock)
        all_questions.extend(questions)
        potential = potential_score(questions)
        snapshots.append(
            {
                "slug": mock.get("slug"),
                "title": mock.get("title"),
                "date": mock.get("attempted_at") or mock.get("imported_at"),
                "score": potential["actual"],
                "potential": potential["potential"],
                "accuracy": _accuracy(questions),
                "attempted": sum(1 for question in questions if question.get("is_attempted")),
            }
        )

    scores = [float(snapshot["score"]) for snapshot in snapshots]
    recent_count = min(3, len(scores))
    recent_average = mean(scores[-recent_count:])
    earlier_scores = scores[:-recent_count]
    trend_delta = recent_average - mean(earlier_scores) if earlier_scores else 0.0
    score_deviation = pstdev(scores) if len(scores) > 1 else 0.0

    type_a = [question for question in all_questions if question.get("difficulty") == "A"]
    type_c = [question for question in all_questions if question.get("difficulty") == "C"]
    time_sinks = [
        question
        for question in all_questions
        if question.get("is_attempted")
        and float(question.get("time_taken") or 0) > 180
        and float(question.get("score") or 0) <= 0
    ]
    banker_conversion = (
        sum(1 for question in type_a if question.get("is_correct")) / len(type_a) * 100
        if type_a
        else 0
    )
    trap_restraint = (
        100
        - sum(
            1
            for question in type_c
            if question.get("is_attempted") and not question.get("is_correct")
        )
        / len(type_c)
        * 100
        if type_c
        else 100
    )
    attempted = [question for question in all_questions if question.get("is_attempted")]
    pace_control = 100 - len(time_sinks) / len(attempted) * 100 if attempted else 100
    consistency = max(0.0, 100 - score_deviation * 3)
    discipline_index = (
        banker_conversion * 0.35
        + trap_restraint * 0.30
        + pace_control * 0.20
        + consistency * 0.15
    )

    section_reports = []
    protocols = []
    for section_slug in ("varc", "dilr", "qa"):
        per_mock = []
        section_questions = []
        for mock in mocks:
            questions = [
                question
                for question in flatten_questions(mock)
                if question.get("section_slug") == section_slug
            ]
            if not questions:
                continue
            section_questions.extend(questions)
            potential = potential_score(questions)
            per_mock.append(
                {
                    "title": mock.get("title"),
                    "score": potential["actual"],
                    "potential": potential["potential"],
                    "attempted": sum(1 for question in questions if question.get("is_attempted")),
                    "accuracy": _accuracy(questions),
                }
            )
        if not per_mock:
            continue

        section_scores = [float(row["score"]) for row in per_mock]
        recent_section_count = min(3, len(section_scores))
        recent_section = mean(section_scores[-recent_section_count:])
        earlier_section = section_scores[:-recent_section_count]
        correct_times = [
            float(question.get("time_taken") or 0)
            for question in section_questions
            if question.get("is_correct") and float(question.get("time_taken") or 0) > 0
        ]
        banker_times = [
            float(question.get("time_taken") or 0)
            for question in section_questions
            if question.get("difficulty") == "A"
            and question.get("is_correct")
            and float(question.get("time_taken") or 0) > 0
        ]
        best_runs = sorted(per_mock, key=lambda row: row["score"], reverse=True)[:3]
        derived_cap = round(min(180, max(90, _percentile(correct_times, 0.75))) / 15) * 15
        section_reports.append(
            {
                "section": section_slug,
                "average_score": _average(section_scores),
                "best_score": max(section_scores),
                "floor_score": min(section_scores),
                "volatility": round(pstdev(section_scores), 1) if len(section_scores) > 1 else 0,
                "trend_delta": round(
                    recent_section - mean(earlier_section) if earlier_section else 0,
                    1,
                ),
                "accuracy": _accuracy(section_questions),
                "average_attempts": _average(row["attempted"] for row in per_mock),
                "potential_gap": round(
                    mean(float(row["potential"]) - float(row["score"]) for row in per_mock),
                    1,
                ),
            }
        )
        protocols.append(
            {
                "section": section_slug,
                "attempt_floor": int(min(row["attempted"] for row in best_runs)),
                "attempt_ceiling": int(max(row["attempted"] for row in best_runs)),
                "accuracy_floor": round(min(float(row["accuracy"]) for row in best_runs), 1),
                "first_pass_cap_seconds": int(derived_cap),
                "banker_median_seconds": round(median(banker_times), 1) if banker_times else 0,
                "basis": "Range observed in your three highest-scoring section runs.",
            }
        )

    error_groups = {
        "omission": [
            question
            for question in all_questions
            if question.get("difficulty") == "A" and not question.get("is_attempted")
        ],
        "selection": [
            question
            for question in all_questions
            if question.get("difficulty") == "C"
            and question.get("is_attempted")
            and not question.get("is_correct")
        ],
        "conversion": [
            question
            for question in all_questions
            if question.get("difficulty") in {"A", "B"}
            and question.get("is_attempted")
            and not question.get("is_correct")
        ],
        "pacing": [
            question
            for question in all_questions
            if question.get("is_correct")
            and float(question.get("topper_avg_time_spend") or 0) > 0
            and float(question.get("time_taken") or 0)
            > float(question.get("topper_avg_time_spend") or 0) * 2.5
        ],
    }
    error_lenses = []
    for kind, questions in error_groups.items():
        error_lenses.append(
            {
                "kind": kind,
                "count": len(questions),
                "marks": round(
                    sum(
                        3 - float(question.get("score") or 0)
                        for question in questions
                        if kind in {"omission", "conversion"}
                    ),
                    1,
                ),
                "minutes": round(
                    sum(float(question.get("time_taken") or 0) for question in questions) / 60,
                    1,
                ),
            }
        )

    pace_definitions = (
        ("under_60", 0, 60),
        ("60_to_120", 60, 120),
        ("120_to_180", 120, 180),
        ("over_180", 180, float("inf")),
    )
    pace_bands = []
    for label, lower, upper in pace_definitions:
        questions = [
            question
            for question in attempted
            if lower < float(question.get("time_taken") or 0) <= upper
            or lower == 0 and 0 <= float(question.get("time_taken") or 0) <= upper
        ]
        minutes = sum(float(question.get("time_taken") or 0) for question in questions) / 60
        score = sum(float(question.get("score") or 0) for question in questions)
        pace_bands.append(
            {
                "band": label,
                "count": len(questions),
                "accuracy": _accuracy(questions),
                "score": round(score, 1),
                "minutes": round(minutes, 1),
                "marks_per_10_minutes": round(score / minutes * 10, 1) if minutes else 0,
            }
        )

    topic_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for question in all_questions:
        topic_groups[_topic_key(question)].append(question)

    topic_matrix = []
    priority_rows = []
    for (section_slug, topic), questions in topic_groups.items():
        topic_attempted = [question for question in questions if question.get("is_attempted")]
        correct = [question for question in topic_attempted if question.get("is_correct")]
        candidate_time = _average(
            float(question.get("time_taken") or 0) for question in topic_attempted
        )
        topper_times = [
            float(question.get("topper_avg_time_spend") or 0)
            for question in topic_attempted
            if float(question.get("topper_avg_time_spend") or 0) > 0
        ]
        topper_time = _average(topper_times)
        pace_ratio = round(candidate_time / topper_time, 2) if topper_time else 0
        accuracy = _accuracy(questions)
        missed_bankers = [
            question
            for question in questions
            if question.get("difficulty") == "A" and not question.get("is_correct")
        ]
        wrong_traps = [
            question
            for question in questions
            if question.get("difficulty") == "C"
            and question.get("is_attempted")
            and not question.get("is_correct")
        ]
        excess_seconds = sum(
            max(
                0,
                float(question.get("time_taken") or 0)
                - float(question.get("topper_avg_time_spend") or 0),
            )
            for question in topic_attempted
            if float(question.get("topper_avg_time_spend") or 0) > 0
        )
        if len(topic_attempted) < 3:
            quadrant = "observe"
        elif accuracy >= 75 and pace_ratio <= 1.35:
            quadrant = "protect"
        elif accuracy >= 75:
            quadrant = "accelerate"
        elif accuracy < 60 and len(wrong_traps) >= max(1, len(topic_attempted) / 3):
            quadrant = "select_better"
        elif accuracy < 60:
            quadrant = "rebuild"
        else:
            quadrant = "sharpen"

        recoverable_marks = sum(
            3 - float(question.get("score") or 0) for question in missed_bankers
        )
        trap_penalties = sum(
            -float(question.get("score") or 0)
            for question in wrong_traps
            if float(question.get("score") or 0) < 0
        )
        priority_score = recoverable_marks * 4 + trap_penalties * 3 + excess_seconds / 120
        topic_matrix.append(
            {
                "section": section_slug,
                "topic": topic,
                "question_count": len(questions),
                "attempted": len(topic_attempted),
                "accuracy": accuracy,
                "score": round(sum(float(question.get("score") or 0) for question in questions), 1),
                "candidate_time_seconds": candidate_time,
                "topper_time_seconds": topper_time,
                "pace_ratio": pace_ratio,
                "missed_bankers": len(missed_bankers),
                "wrong_traps": len(wrong_traps),
                "excess_minutes": round(excess_seconds / 60, 1),
                "quadrant": quadrant,
                "priority_score": round(priority_score, 1),
            }
        )
        if missed_bankers:
            priority_rows.append(
                {
                    "kind": "banker_conversion",
                    "section": section_slug,
                    "topic": topic,
                    "title": f"Convert {topic} bankers",
                    "detail": f"{len(missed_bankers)} Type A misses across {len(questions)} questions.",
                    "metric": f"+{round(recoverable_marks, 1):g} mark bridge",
                    "priority_score": round(recoverable_marks * 4, 1),
                }
            )
        if wrong_traps:
            priority_rows.append(
                {
                    "kind": "selection",
                    "section": section_slug,
                    "topic": topic,
                    "title": f"Exit {topic} traps earlier",
                    "detail": f"{len(wrong_traps)} low-consensus wrong attempts used {round(sum(float(question.get('time_taken') or 0) for question in wrong_traps) / 60, 1):g} minutes.",
                    "metric": f"{round(trap_penalties, 1):g} penalties",
                    "priority_score": round(len(wrong_traps) * 2 + trap_penalties * 3, 1),
                }
            )
        if excess_seconds >= 300 and len(topic_attempted) >= 3:
            priority_rows.append(
                {
                    "kind": "pacing",
                    "section": section_slug,
                    "topic": topic,
                    "title": f"Compress {topic} execution",
                    "detail": f"Candidate time exceeded topper time by {round(excess_seconds / 60, 1):g} minutes.",
                    "metric": f"{pace_ratio:g}x pace",
                    "priority_score": round(excess_seconds / 120, 1),
                }
            )

    topic_matrix.sort(key=lambda row: row["priority_score"], reverse=True)
    priority_rows.sort(key=lambda row: row["priority_score"], reverse=True)

    practice_queue = []
    for question in all_questions:
        topper_accuracy = float(question.get("topper_p_value") or 0)
        topper_time = float(question.get("topper_avg_time_spend") or 0)
        candidate_time = float(question.get("time_taken") or 0)
        if topper_accuracy > 0.80 and not question.get("is_correct"):
            reason = "Consensus miss"
            priority = 130 + topper_accuracy * 10
        elif question.get("difficulty") == "A" and not question.get("is_correct"):
            reason = "Type A conversion"
            priority = 120 + topper_accuracy * 10
        elif (
            question.get("difficulty") == "B"
            and question.get("is_attempted")
            and not question.get("is_correct")
        ):
            reason = "Type B execution"
            priority = 85 + topper_accuracy * 10
        elif (
            question.get("is_correct")
            and topper_time > 0
            and candidate_time > topper_time * 2.5
        ):
            reason = "Speed reconstruction"
            priority = 55 + candidate_time / topper_time
        elif (
            question.get("difficulty") == "C"
            and question.get("is_attempted")
            and not question.get("is_correct")
        ):
            reason = "Selection review"
            priority = 45 + candidate_time / 60
        else:
            continue
        practice_queue.append(
            {
                **_question_ref(question),
                "reason": reason,
                "priority": round(priority, 1),
            }
        )
    practice_queue.sort(key=lambda row: row["priority"], reverse=True)

    return {
        "mock_count": len(mocks),
        "scorecard": {
            "average_score": round(mean(scores), 1),
            "best_score": round(max(scores), 1),
            "floor_score": round(min(scores), 1),
            "volatility": round(score_deviation, 1),
            "recent_average": round(recent_average, 1),
            "trend_delta": round(trend_delta, 1),
            "average_potential_gap": round(
                mean(float(snapshot["potential"]) - float(snapshot["score"]) for snapshot in snapshots),
                1,
            ),
            "discipline_index": round(discipline_index, 1),
            "discipline_components": {
                "banker_conversion": round(banker_conversion, 1),
                "trap_restraint": round(trap_restraint, 1),
                "pace_control": round(pace_control, 1),
                "consistency": round(consistency, 1),
            },
        },
        "trajectory": snapshots,
        "sections": section_reports,
        "error_lenses": error_lenses,
        "pace_bands": pace_bands,
        "topic_matrix": topic_matrix,
        "priorities": priority_rows[:10],
        "protocol": protocols,
        "practice_queue": practice_queue[:18],
        "methodology": {
            "discipline_index": "35% banker conversion + 30% trap restraint + 20% pace control + 15% score consistency.",
            "topic_quadrants": "Based only on attempted accuracy, candidate/topper pace ratio, and low-consensus wrong attempts.",
            "protocol": "Attempt ranges come from the three highest-scoring historical runs in each section.",
        },
    }