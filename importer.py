from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Iterable

import requests

from analytics import classify_question
from storage import MockStore


API_BASE = "https://api.test-player.imsindia.com"
TOKEN_PATTERN = re.compile(r"(?:[?&]token=)([A-Za-z0-9_.-]+)")


def extract_token(url: str) -> str:
    match = TOKEN_PATTERN.search(url.strip())
    if not match:
        raise ValueError("The IMS URL does not contain a valid token parameter.")
    return match.group(1)


def _first(mapping: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


def _find_value(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in keys and nested is not None:
                return nested
        for nested in value.values():
            result = _find_value(nested, keys)
            if result is not None:
                return result
    elif isinstance(value, list):
        for nested in value:
            result = _find_value(nested, keys)
            if result is not None:
                return result
    return None


def _find_sections(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        groups = value.get("groups")
        if isinstance(groups, list):
            sections = [
                section
                for group in groups
                if isinstance(group, dict)
                for section in group.get("sections", [])
                if isinstance(section, dict)
            ]
            if sections:
                return sections
        for key in ("sections", "section_details", "question_bank"):
            candidate = value.get(key)
            if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):
                return candidate
        for nested in value.values():
            result = _find_sections(nested)
            if result:
                return result
    elif isinstance(value, list):
        for nested in value:
            result = _find_sections(nested)
            if result:
                return result
    return []


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "yes", "y", "1", "correct", "attempted"}:
            return True
        if normalized in {"false", "no", "n", "0", "incorrect", "unattempted", "skipped"}:
            return False
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ratio(value: Any) -> float | None:
    if value is None or value == "":
        return None
    result = _as_float(value)
    return round(result / 100 if result > 1 else result, 4)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or f"mock-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"


def _decode_content(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return value
    return decoded if "<" in decoded or ">" in decoded else value


def _decode_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _attempts_by_question(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload:
        return {}
    attempts = {}
    for section in _find_sections(payload):
        rows = _first(section, ("questions", "question_details", "question_list"), [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                question_id = _first(row, ("question_id", "id", "_id"))
                if question_id is not None:
                    attempts[str(question_id)] = row
    return attempts


def _question_list(
    section: dict[str, Any], attempts: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    questions = _first(section, ("questions", "question_details", "question_list"), [])
    if isinstance(questions, dict):
        questions = list(questions.values())
    flattened = []
    for wrapper in questions:
        if not isinstance(wrapper, dict):
            continue
        question_data = wrapper.get("question_data")
        nested_questions = question_data.get("questions") if isinstance(question_data, dict) else None
        if not isinstance(nested_questions, list):
            flattened.append(wrapper)
            continue

        scoring = {
            str(item.get("question_id")): item
            for item in wrapper.get("scoring", [])
            if isinstance(item, dict) and item.get("question_id") is not None
        }
        passage = _first(question_data, ("passage", "source_material"))
        for nested_question in nested_questions:
            if not isinstance(nested_question, dict):
                continue
            question_id = str(
                _first(nested_question, ("question_id", "id", "_id"), "")
            )
            flattened.append(
                {
                    **nested_question,
                    "_attempt": attempts.get(question_id, {}),
                    "_scoring": scoring.get(question_id, {}),
                    "_passage": passage,
                }
            )
    return flattened


def _normalize_options(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    options = []
    for index, option in enumerate(value, start=1):
        if isinstance(option, dict):
            option_content = _first(
                option,
                ("option_title", "title", "text", "label", "option"),
                "",
            )
            options.append(
                {
                    "id": str(_first(option, ("id", "option_id", "value"), index)),
                    "html": _decode_content(option_content),
                    "is_correct": _as_bool(_first(option, ("is_correct", "correct"), False)),
                }
            )
        else:
            options.append(
                {
                    "id": str(index),
                    "html": _decode_content(option),
                    "is_correct": False,
                }
            )
    return options


def _normalize_question(
    question: dict[str, Any], section_slug: str, index: int
) -> dict[str, Any]:
    attempt = question.get("_attempt")
    if not isinstance(attempt, dict):
        attempt = _first(
            question,
            ("candidate_response", "student_response", "attempt_details", "candidate_attempt"),
            {},
        )
    response = question.get("response")
    response = response if isinstance(response, dict) else {}
    attempt = attempt if isinstance(attempt, dict) else {}
    source = {**question, **response, **attempt}

    options_value = _first(question, ("options", "answer_options", "choices"), [])
    if not isinstance(options_value, list):
        decoded_options = _decode_json(options_value)
        options_value = decoded_options if isinstance(decoded_options, list) else []
    options = _normalize_options(options_value)
    candidate_answer = _first(
        source,
        (
            "candidate_answer",
            "selected_answer",
            "given_answer",
            "user_response",
            "answer",
        ),
    )
    status = str(_first(source, ("status", "evaluation_status"), "")).casefold()
    is_attempted = status in {"correct", "incorrect", "answered", "marked_for_review"}
    if not status:
        is_attempted = _as_bool(
            _first(source, ("is_attempted", "attempted", "isAnswered")),
            candidate_answer not in (None, "", [], {}),
        )
    is_correct = status == "correct" or (
        not status
        and _as_bool(_first(source, ("is_correct", "correct", "isCorrect"), False))
    )

    question_type = str(
        _first(
            question,
            ("question_type", "question_type_name", "type"),
            "MCQ" if options else "TITA",
        )
    ).casefold()
    is_tita = any(
        label in question_type
        for label in ("tita", "non-mcq", "type-in-the-answer", "type in the answer")
    )
    scoring = question.get("_scoring")
    scoring = scoring if isinstance(scoring, dict) else {}
    if status == "correct":
        score = _as_float(scoring.get("correct_answer"), 3)
    elif status == "incorrect":
        score = _as_float(scoring.get("incorrect_answer"), 0 if is_tita else -1)
    elif status:
        score = 0
    else:
        score = 3 if is_correct else (0 if not is_attempted or is_tita else -1)

    advance_statistics = attempt.get("advance_statistics")
    advance_statistics = advance_statistics if isinstance(advance_statistics, dict) else {}
    overall = advance_statistics.get("overall_statistics")
    overall = overall if isinstance(overall, dict) else {}
    topper = advance_statistics.get("toppers_statistics")
    if not isinstance(topper, dict):
        topper = _first(question, ("toppers_statistics", "topper_statistics"), {})
    if not isinstance(topper, dict):
        topper = {}
    p_value = _ratio(
        _first(overall, ("p_value", "accuracy_percentage"), _first(
            question, ("p_value", "accuracy", "correct_percentage")
        ))
    )
    topper_p_value = _ratio(
        _first(topper, ("p_value", "accuracy_percentage", "accuracy", "correct_percentage"))
    )
    topper_attempt = _ratio(
        _first(topper, ("attempt_percentage", "attempt_percent", "attempt_rate"))
    )
    prompt = _decode_content(
        _first(question, ("question_title", "question", "title", "text"), "")
    )
    passage = _decode_content(question.get("_passage"))
    question_html = f"{passage}{prompt}" if passage and passage not in prompt else prompt
    review = question.get("review")
    review = review if isinstance(review, dict) else {}
    solution_html = _decode_content(
        _first(
            question,
            ("solution", "explanation", "solution_text"),
            _first(review, ("text", "solution", "explanation"), ""),
        )
    )

    if "time_taken" in attempt:
        time_taken = _as_float(attempt.get("time_taken")) / 1000
    else:
        time_taken = _as_float(_first(source, ("time_taken", "time_spent", "timeSpend")))
    if "average_time_taken" in overall:
        average_time = _as_float(overall.get("average_time_taken")) / 1000
    else:
        average_time = _as_float(
            _first(question, ("avg_time_spend", "average_time", "avg_time_taken"))
        )
    if "average_time_taken" in topper:
        topper_average_time = _as_float(topper.get("average_time_taken")) / 1000
    else:
        topper_average_time = _as_float(
            _first(topper, ("avg_time_spend", "average_time", "avg_time_taken"))
        )

    return {
        "id": str(_first(question, ("id", "question_id", "questionId"), f"{section_slug}-{index}")),
        "number": index,
        "section_slug": section_slug,
        "question_html": question_html,
        "solution_html": solution_html,
        "options": options,
        "question_type": "TITA" if is_tita else "MCQ",
        "candidate_answer": candidate_answer,
        "correct_answer": _decode_json(
            _first(question, ("correct_answer", "answer_key", "right_answer"))
        ),
        "is_attempted": is_attempted,
        "is_correct": is_correct,
        "time_taken": round(time_taken, 1),
        "score": round(score, 1),
        "p_value": p_value,
        "avg_time_spend": round(average_time, 1),
        "topper_p_value": topper_p_value,
        "topper_avg_time_spend": round(topper_average_time, 1),
        "topper_attempt_percentage": topper_attempt,
        "subject": str(_first(question, ("subject_name", "subject", "area"), "Unclassified")),
        "topic": str(_first(question, ("topic_name", "topic"), "Unclassified")),
        "sub_topic": str(_first(question, ("sub_topic_name", "sub_topic"), "Unclassified")),
        "difficulty": classify_question(p_value, topper_p_value, topper_attempt),
    }


def normalize_mock(
    details_payload: dict[str, Any],
    question_payload: dict[str, Any],
    instruction_payload: dict[str, Any],
    attempt_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = str(
        _find_value(details_payload, {"test_title", "test_name", "title", "name"})
        or "Imported IMS Mock"
    )
    sections = _find_sections(question_payload)
    attempts = _attempts_by_question(attempt_payload)
    normalized_sections = []
    for section_index, section in enumerate(sections, start=1):
        section_title = str(
            _first(section, ("title", "section_name", "name"), f"Section {section_index}")
        )
        section_slug = _section_slug(section_title, section_index)
        questions = [
            _normalize_question(question, section_slug, index)
            for index, question in enumerate(_question_list(section, attempts), start=1)
        ]
        normalized_sections.append(
            {
                "id": str(_first(section, ("id", "section_id"), section_index)),
                "slug": section_slug,
                "title": section_title,
                "duration_minutes": _section_duration(section, details_payload, len(sections)),
                "questions": questions,
            }
        )

    imported_at = datetime.now(UTC).isoformat()
    duration_milliseconds = _find_value(details_payload, {"timeDurationInMilliSeconds"})
    instructions = _find_value(
        instruction_payload, {"instructions", "instruction", "description"}
    )
    return {
        "slug": _slugify(title),
        "title": title,
        "imported_at": imported_at,
        "attempted_at": _find_value(
            details_payload,
            {"attempted_at", "submission_time", "completed_at", "test_date"},
        ),
        "duration_minutes": round(
            _as_float(duration_milliseconds) / 60000
            if duration_milliseconds is not None
            else _as_float(
                _find_value(details_payload, {"total_duration", "duration", "test_duration"})
            ),
            1,
        ),
        "instructions_html": _normalize_instructions(instructions),
        "sections": normalized_sections,
    }


def _section_duration(
    section: dict[str, Any], details_payload: dict[str, Any], section_count: int
) -> float:
    milliseconds = section.get("timeDurationInMilliSeconds")
    if milliseconds is not None:
        return round(_as_float(milliseconds) / 60000, 1)
    explicit = _first(section, ("duration", "section_duration", "time_limit"))
    if explicit is not None:
        return round(_as_float(explicit), 1)
    total = _find_value(details_payload, {"timeDurationInMilliSeconds"})
    return round(_as_float(total) / 60000 / section_count, 1) if total and section_count else 0


def _normalize_instructions(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            content = _first(item, ("instructions", "instruction", "description")) \
                if isinstance(item, dict) else item
            decoded = _decode_content(content)
            if decoded:
                parts.append(decoded)
        return "\n".join(parts)
    return _decode_content(value)


def _section_slug(title: str, section_index: int) -> str:
    normalized = title.casefold()
    if "verbal" in normalized or "varc" in normalized or "reading" in normalized:
        return "varc"
    if "data" in normalized or "logical" in normalized or "dilr" in normalized:
        return "dilr"
    if "quant" in normalized or normalized.strip() == "qa":
        return "qa"
    return f"section-{section_index}"


def _fetch(
    session: requests.Session, path: str, token: str, session_id: str
) -> dict[str, Any]:
    response = session.get(
        f"{API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "session-id": session_id,
            "User-Agent": "Mozilla/5.0",
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"IMS {path} returned an unexpected response.")
    return payload


def import_mock(
    url: str,
    *,
    store: MockStore | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    token = extract_token(url)
    client = session or requests.Session()
    session_id = str(uuid.uuid4())
    test_info = _fetch(client, "/test/info", token, session_id)
    attempt_info = _fetch(client, "/test-attempts/attempt-info", token, session_id)
    mock = normalize_mock(test_info, test_info, test_info, attempt_info)
    (store or MockStore()).upsert(mock)
    return mock