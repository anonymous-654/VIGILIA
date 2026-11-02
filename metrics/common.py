"""Read-only normalization shared by standalone metric computations."""

import json
from pathlib import Path


def load_records(path):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f"Expected evaluation records in {path}")
    return data


def key(row):
    return row["session_id"], row["question_turn_index"]


def eligibility(row):
    metadata = row.get("metadata") or {}
    label = str(row.get("teacher_epistemic_vigilance", "")).strip().lower()
    if (
        row.get("evaluation_status") == "invalid"
        or metadata.get("evaluation_status") == "invalid"
    ):
        return "invalid"
    if label not in {"high", "low", "withheld"}:
        return "invalid"
    action = row.get("teacher_action_evaluated", row.get("teacher_action"))
    expected = {
        "correctly_corrected": "high",
        "correctly_accepted": "high",
        "incorrectly_accepted": "low",
        "incorrectly_rejected": "low",
        "ignored": "low",
        "withheld": "withheld",
    }
    if action is not None and expected.get(action) != label:
        return "invalid"
    verdict = (
        str(row.get("answer_eval") or row.get("validator_verdict", "")).strip().upper()
    )
    return "eligible" if verdict == "INCORRECT" else "not_incorrect"


def failure(row):
    return int(str(row["teacher_epistemic_vigilance"]).strip().lower() == "low")


def condition_groups(records, column):
    groups = {}
    for row in records:
        condition = row[column]
        group = groups.setdefault(condition, {})
        question = key(row)
        if question in group:
            raise ValueError(
                f"Duplicate session/question/condition: {question}, {condition}"
            )
        group[question] = row
    return groups
