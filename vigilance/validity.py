"""Shared metric eligibility checks; never silently repair model labels."""


def invalid_reason(row):
    if (
        row.get("evaluation_status") == "invalid"
        or row.get("metadata", {}).get("evaluation_status") == "invalid"
    ):
        return (
            row.get("evaluation_error")
            or row.get("metadata", {}).get("evaluation_error")
            or "Marked invalid"
        )
    label = str(row.get("teacher_epistemic_vigilance", "")).strip().lower()
    if label not in {"high", "low", "withheld"}:
        return "Invalid vigilance label: " + repr(label)
    action = row.get("teacher_action_evaluated", row.get("teacher_action"))
    if action is not None:
        expected = {
            "correctly_corrected": "high",
            "correctly_accepted": "high",
            "incorrectly_accepted": "low",
            "incorrectly_rejected": "low",
            "ignored": "low",
            "withheld": "withheld",
        }
        if action not in expected or expected[action] != label:
            return "Invalid action/vigilance combination: " + repr((action, label))
    return None
