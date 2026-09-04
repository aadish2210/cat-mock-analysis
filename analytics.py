from __future__ import annotations

from collections import defaultdict
from math import floor
from typing import Any, Iterable


def classify_question(
    p_value: float | None,
    topper_p_value: float | None,
    topper_attempt_percentage: float | None,
) -> str:
    """Classify a question using the strongest available empirical signal."""
    if (
        topper_p_value is not None
        and topper_attempt_percentage is not None
        and topper_p_value < 0.50
        and topper_attempt_percentage < 0.40
    ):
        return "C"
    if (p_value is not None and p_value >= 0.60) or (
        topper_p_value is not None and topper_p_value >= 0.85
    ):
        return "A"
    if p_value is not None and p_value < 0.35:
        return "C"
    return "B"


def potential_score(questions: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(questions)
    actual = sum(float(question.get("score") or 0) for question in rows)
    traps_avoided = sum(
        -float(question.get("score") or 0)
        for question in rows
        if question.get("difficulty") == "C" and float(question.get("score") or 0) < 0
    )
    skipped_type_a = [
        question
        for question in rows
        if question.get("difficulty") == "A" and not question.get("is_attempted")
    ]
    incorrect_type_a = [
        question
        for question in rows
        if question.get("difficulty") == "A"
        and question.get("is_attempted")
        and not question.get("is_correct")
    ]
    skipped_gain = len(skipped_type_a) * 3
    incorrect_gain = sum(3 - float(question.get("score") or 0) for question in incorrect_type_a)

    return {
        "actual": round(actual, 1),
        "traps_avoided": round(traps_avoided, 1),
        "skipped_type_a_count": len(skipped_type_a),
        "skipped_type_a_gain": skipped_gain,
        "incorrect_type_a_count": len(incorrect_type_a),
        "incorrect_type_a_gain": round(incorrect_gain, 1),
        "potential": round(actual + traps_avoided + skipped_gain + incorrect_gain, 1),
    }


def simulate_questions(
    questions: Iterable[dict[str, Any]],
    *,
    time_cap_seconds: int = 180,
    topic_blacklists: Iterable[str] = (),
    type_c_immunity: bool = True,
    type_a_conversion_rate: float = 0.50,
) -> dict[str, Any]:
    if time_cap_seconds not in {120, 150, 180}:
        raise ValueError("time_cap_seconds must be 120, 150, or 180")
    if not 0 <= type_a_conversion_rate <= 1:
        raise ValueError("type_a_conversion_rate must be between 0 and 1")

    blacklists = {topic.casefold() for topic in topic_blacklists}
    rows = list(questions)
    actual = sum(float(question.get("score") or 0) for question in rows)
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in rows:
        by_section[str(question.get("section_slug") or "unknown")].append(question)

    sections = []
    total_penalties_saved = 0.0
    total_conversion_gain = 0.0
    total_freed_seconds = 0.0

    for section_slug, section_questions in by_section.items():
        freed_seconds = 0.0
        penalties_saved = 0.0
        affected_ids: set[Any] = set()

        for question in section_questions:
            if not question.get("is_attempted") or float(question.get("score") or 0) > 0:
                continue
            topic = str(question.get("topic") or "").casefold()
            remove_attempt = topic in blacklists or (
                type_c_immunity and question.get("difficulty") == "C"
            )
            time_taken = float(question.get("time_taken") or 0)
            if remove_attempt:
                freed_seconds += time_taken
                affected_ids.add(question.get("id"))
            elif time_taken > time_cap_seconds:
                freed_seconds += time_taken - time_cap_seconds
                affected_ids.add(question.get("id"))

            if question.get("id") in affected_ids and float(question.get("score") or 0) < 0:
                penalties_saved += -float(question.get("score") or 0)

        available_type_a = sum(
            1
            for question in section_questions
            if question.get("difficulty") == "A"
            and (not question.get("is_attempted") or not question.get("is_correct"))
            and str(question.get("topic") or "").casefold() not in blacklists
        )
        available_points = available_type_a * 3
        capacity_points = floor((freed_seconds / 60) / 2.0) * 3
        conversion_gain = min(available_points * type_a_conversion_rate, capacity_points)

        total_freed_seconds += freed_seconds
        total_penalties_saved += penalties_saved
        total_conversion_gain += conversion_gain
        sections.append(
            {
                "section": section_slug,
                "freed_minutes": round(freed_seconds / 60, 1),
                "penalties_saved": round(penalties_saved, 1),
                "available_type_a_points": available_points,
                "conversion_gain": round(conversion_gain, 1),
            }
        )

    return {
        "actual_score": round(actual, 1),
        "penalties_saved": round(total_penalties_saved, 1),
        "freed_minutes": round(total_freed_seconds / 60, 1),
        "conversion_gain": round(total_conversion_gain, 1),
        "simulated_score": round(actual + total_penalties_saved + total_conversion_gain, 1),
        "sections": sections,
    }