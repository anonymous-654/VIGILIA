import json
import re
from typing import Any


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    return text


def repair_bare_backslashes(text: str) -> str:
    repaired = []
    i = 0
    while i < len(text):
        char = text[i]
        if char != "\\":
            repaired.append(char)
            i += 1
            continue

        next_char = text[i + 1] if i + 1 < len(text) else ""
        if next_char in {'"', "\\", "/"}:
            repaired.append(char)
            repaired.append(next_char)
            i += 2
        elif next_char == "u" and re.match(r"^[0-9a-fA-F]{4}", text[i + 2 : i + 6]):
            repaired.append(text[i : i + 6])
            i += 6
        else:
            repaired.append("\\\\")
            i += 1

    return "".join(repaired)


def repair_escaped_value_delimiters(text: str) -> str:
    """Repair string values incorrectly delimited with ``\\"``.

    Some LLM responses put a backslash before the opening and closing quotes
    of a JSON value, for example ``"evidence_span": \\"text\\"``. Restrict
    the repair to complete values after a colon and before a JSON separator so
    escaped quotes inside otherwise valid strings remain unchanged.
    """
    malformed_value = re.compile(
        r'(?P<prefix>:\s*)\\"(?P<value>.*?)\\""?(?=\s*[,}\]])',
        flags=re.DOTALL,
    )
    return malformed_value.sub(
        lambda match: (f'{match.group("prefix")}"{match.group("value")}"'),
        text,
    )


def repair_trailing_commas(text: str) -> str:
    """Remove a trailing comma immediately before ``}`` or ``]``."""
    return re.sub(r",(?=\s*[}\]])", "", text)


def parse_fenced_json_response(text: str) -> Any:
    cleaned = strip_json_fence(text)
    original_error = None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        original_error = exc

    delimiter_repaired = repair_escaped_value_delimiters(cleaned)
    candidates = [
        delimiter_repaired,
        repair_bare_backslashes(delimiter_repaired),
        repair_trailing_commas(delimiter_repaired),
        repair_trailing_commas(repair_bare_backslashes(delimiter_repaired)),
    ]

    if "Invalid \\escape" in str(original_error):
        candidates.append(repair_bare_backslashes(cleaned))

    seen = {cleaned}
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise original_error
