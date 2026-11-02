import re

from llm.client import query_corruption_json_llm
from core.language_phen import (
    LANGUAGE_PHENOMENA,
    LANGUAGE_PHENOMENON_DESCRIPTIONS,
    format_phenomenon_items,
)
from corruption.prompts import (
    LANGUAGE_PHENOMENON_CORRUPTION_PROMPT,
)
from corruption.validators import validate_incorrectness
from schemas import LanguagePhenomenonCorruptionRecord


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _validate_selected_items(
    answer: str, selected_items: list[str], allowed_items: list[str]
) -> tuple[bool, str]:
    if not selected_items:
        return False, "No selected phenomenon items were returned."

    invalid_items = [item for item in selected_items if item not in allowed_items]
    if invalid_items:
        return (
            False,
            f"Selected items are not in the allowed phenomenon list: {invalid_items}",
        )

    missing_items = [
        item for item in selected_items if item.lower() not in answer.lower()
    ]
    if missing_items:
        return (
            False,
            f"Selected items are not visibly present in the updated answer: {missing_items}",
        )

    return True, "Selected items are allowed and visibly present in the updated answer."


def apply_language_phenomenon_corruption(
    model_path: str,
    session_id: str,
    question_turn_index: int,
    question_turn_number: int,
    question_text: str,
    base_wrong_answer: str,
    phenomenon_type: str,
    degree: int = 1,
    max_retries: int = 3,
) -> LanguagePhenomenonCorruptionRecord:
    if phenomenon_type not in LANGUAGE_PHENOMENA:
        raise ValueError(f"Unknown language phenomenon: {phenomenon_type}")

    allowed_items = LANGUAGE_PHENOMENA[phenomenon_type]
    selected_items = []
    selection_reason = ""
    best_answer = base_wrong_answer
    num_instances = 0
    selected_item_passed = False
    selected_item_reason = ""
    incorrect_passed = False
    incorrect_reason = ""

    for _ in range(max_retries):
        prompt = LANGUAGE_PHENOMENON_CORRUPTION_PROMPT.format(
            QUESTION=question_text,
            BASE_WRONG_ANSWER=base_wrong_answer,
            PHENOMENON_TYPE=phenomenon_type,
            PHENOMENON_DESCRIPTION=LANGUAGE_PHENOMENON_DESCRIPTIONS[phenomenon_type],
            PHENOMENON_ITEMS=format_phenomenon_items(phenomenon_type),
            DEGREE=degree,
        )
        obj, _, _ = query_corruption_json_llm(
            sys_prompt=prompt, user_prompt="", temperature=0.5
        )

        raw_selected_items = obj.get("selected_items", obj.get("selected_item", []))
        if isinstance(raw_selected_items, str):
            selected_items = [raw_selected_items.strip()]
        else:
            selected_items = [str(item).strip() for item in raw_selected_items]
        selected_items = [item for item in selected_items if item]

        selection_reason = str(obj["selection_reason"]).strip()
        num_instances = _safe_int(obj.get("num_instances"), len(selected_items))
        candidate = str(
            obj.get("updated_text", obj.get("updated_wrong_answer", ""))
        ).strip()

        selected_item_passed, selected_item_reason = _validate_selected_items(
            candidate,
            selected_items,
            allowed_items,
        )
        incorrect_passed, _, incorrect_reason = validate_incorrectness(
            question_text, candidate
        )
        best_answer = candidate

        if selected_item_passed and incorrect_passed:
            break

    return LanguagePhenomenonCorruptionRecord(
        session_id=session_id,
        question_turn_index=question_turn_index,
        question_turn_number=question_turn_number,
        phenomenon_type=phenomenon_type,
        degree=degree,
        record_type="language_phenomenon",
        num_added_words=max(
            count_words(best_answer) - count_words(base_wrong_answer), 0
        ),
        selected_item=", ".join(selected_items),
        selected_items=selected_items,
        num_instances=num_instances,
        selection_reason=selection_reason,
        base_wrong_answer=base_wrong_answer,
        updated_wrong_answer=best_answer,
        selected_item_validator_passed=selected_item_passed,
        selected_item_validator_reason=selected_item_reason,
        answer_eval="INCORRECT" if incorrect_passed else "CORRECT",
        incorrect_validator_passed=incorrect_passed,
        incorrect_validator_reason=incorrect_reason,
    )
