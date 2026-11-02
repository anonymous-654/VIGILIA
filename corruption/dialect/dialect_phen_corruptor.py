import re
from typing import Any, Dict

from corruption.dialect.phenomena import get_dialect_phenomenon
from corruption.dialect.prompts import (
    DIALECT_PHENOMENON_CORRUPTION_PROMPT,
    DIALECT_PHENOMENON_VALIDATOR_PROMPT,
)
from corruption.validators import validate_incorrectness
from llm.client import query_corruption_json_llm, query_small_json_llm
from schemas import DialectPhenomenonCorruptionRecord


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _validate_dialect_rewrite(
    phenomenon_type: str,
    phenomenon: Dict[str, str],
    base_wrong_answer: str,
    updated_wrong_answer: str,
    evidence_span: str,
) -> tuple[bool, str]:
    prompt = DIALECT_PHENOMENON_VALIDATOR_PROMPT.format(
        PHENOMENON_NAME=phenomenon["display_name"],
        PHENOMENON_TYPE=phenomenon_type,
        PHENOMENON_DEFINITION=phenomenon["definition"],
        BASE_WRONG_ANSWER=base_wrong_answer,
        UPDATED_WRONG_ANSWER=updated_wrong_answer,
        EVIDENCE_SPAN=evidence_span,
    )
    obj, _, _ = query_small_json_llm(
        sys_prompt=prompt,
        user_prompt="",
        temperature=0,
    )
    phenomenon_present = _as_bool(obj.get("phenomenon_present"))
    content_preserved = _as_bool(obj.get("content_preserved"))
    reason = (
        f"Phenomenon: {obj.get('phenomenon_reason', '')} "
        f"Content preservation: {obj.get('content_reason', '')}"
    ).strip()
    return phenomenon_present and content_preserved, reason


def apply_dialect_phenomenon_corruption(
    model_path: str,
    session_id: str,
    question_turn_index: int,
    question_turn_number: int,
    question_text: str,
    base_wrong_answer: str,
    phenomenon_type: str,
    max_retries: int = 3,
) -> DialectPhenomenonCorruptionRecord:
    del model_path  # Answer rewrites use the configured Azure helper.
    phenomenon = get_dialect_phenomenon(phenomenon_type)

    applicable = False
    applicability_reason = ""
    evidence_span = ""
    selection_reason = ""
    best_answer = base_wrong_answer
    dialect_passed = False
    dialect_reason = "The phenomenon was not applied."

    for _ in range(max_retries):
        prompt = DIALECT_PHENOMENON_CORRUPTION_PROMPT.format(
            QUESTION=question_text,
            BASE_WRONG_ANSWER=base_wrong_answer,
            PHENOMENON_NAME=phenomenon["display_name"],
            PHENOMENON_TYPE=phenomenon_type,
            PHENOMENON_DEFINITION=phenomenon["definition"],
            APPLICATION_GUIDANCE=phenomenon["application_guidance"],
        )
        obj, _, _ = query_corruption_json_llm(
            sys_prompt=prompt,
            user_prompt="",
            temperature=0.4,
        )

        applicable = _as_bool(obj.get("applicable"))
        applicability_reason = str(obj.get("applicability_reason", "")).strip()
        selection_reason = str(obj.get("selection_reason", "")).strip()
        evidence_span = str(obj.get("evidence_span", "")).strip()
        candidate = str(obj.get("updated_text", base_wrong_answer)).strip()

        if not applicable:
            best_answer = base_wrong_answer
            evidence_span = ""
            dialect_passed = True
            dialect_reason = "Not applicable: " + applicability_reason
            break

        best_answer = candidate

        dialect_passed, dialect_reason = _validate_dialect_rewrite(
            phenomenon_type=phenomenon_type,
            phenomenon=phenomenon,
            base_wrong_answer=base_wrong_answer,
            updated_wrong_answer=candidate,
            evidence_span=evidence_span,
        )
        if dialect_passed:
            break

    incorrect_passed, _, incorrect_reason = validate_incorrectness(
        question_text,
        best_answer,
    )

    return DialectPhenomenonCorruptionRecord(
        session_id=session_id,
        question_turn_index=question_turn_index,
        question_turn_number=question_turn_number,
        phenomenon_type=phenomenon_type,
        phenomenon_definition=phenomenon["definition"],
        yale_url=phenomenon["yale_url"],
        applicable=applicable,
        applicability_reason=applicability_reason,
        num_added_words=max(
            count_words(best_answer) - count_words(base_wrong_answer), 0
        ),
        selected_item=evidence_span,
        selected_items=[evidence_span] if evidence_span else [],
        num_instances=1 if evidence_span else 0,
        selection_reason=selection_reason,
        base_wrong_answer=base_wrong_answer,
        updated_wrong_answer=best_answer,
        selected_item_validator_passed=dialect_passed,
        selected_item_validator_reason=dialect_reason,
        answer_eval="INCORRECT" if incorrect_passed else "CORRECT",
        incorrect_validator_passed=incorrect_passed,
        incorrect_validator_reason=incorrect_reason,
    )
