import json
import re
from typing import Any, Dict, List

from corruption.dialect_speaker.prompts import (
    DIALECT_SPEAKER_PROMPTS,
    DIALECT_SPEAKER_VALIDATOR_PROMPT,
    build_dialect_speaker_prompt,
)
from corruption.validators import validate_incorrectness
from llm.client import query_corruption_json_llm, query_small_json_llm
from schemas import DialectSpeakerCorruptionRecord


def count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _normalize_features(value: Any) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_evidence(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []

    evidence = []
    for item in value:
        if not isinstance(item, dict):
            continue
        feature = str(item.get("feature", "")).strip()
        span = str(item.get("evidence_span", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        if feature and span:
            evidence.append(
                {
                    "feature": feature,
                    "evidence_span": span,
                    "explanation": explanation,
                }
            )
    return evidence


def _validate_dialect_speaker_rewrite(
    dialect_type: str,
    base_wrong_answer: str,
    updated_wrong_answer: str,
    feature_evidence: List[Dict[str, str]],
) -> tuple[bool, str]:
    prompt = DIALECT_SPEAKER_VALIDATOR_PROMPT.format(
        DIALECT_NAME=dialect_type,
        BASE_WRONG_ANSWER=base_wrong_answer,
        UPDATED_WRONG_ANSWER=updated_wrong_answer,
        FEATURE_EVIDENCE=json.dumps(feature_evidence, ensure_ascii=False),
    )
    obj, _, _ = query_small_json_llm(
        sys_prompt=prompt,
        user_prompt="",
        temperature=0,
    )
    dialect_present = _as_bool(obj.get("dialect_present"))
    content_preserved = _as_bool(obj.get("content_preserved"))
    reason = (
        f"Dialect: {obj.get('dialect_reason', '')} "
        f"Content preservation: {obj.get('content_reason', '')}"
    ).strip()
    return dialect_present and content_preserved, reason


def apply_dialect_speaker_corruption(
    model_path: str,
    session_id: str,
    question_turn_index: int,
    question_turn_number: int,
    question_text: str,
    base_wrong_answer: str,
    dialect_type: str,
    max_retries: int = 3,
) -> DialectSpeakerCorruptionRecord:
    del model_path  # Answer rewrites use the configured Azure helper.
    if dialect_type not in DIALECT_SPEAKER_PROMPTS:
        choices = ", ".join(sorted(DIALECT_SPEAKER_PROMPTS))
        raise ValueError(
            f"Unknown dialect speaker type: {dialect_type}. Choose: {choices}"
        )

    applicable = False
    applicability_reason = ""
    applied_features: List[str] = []
    feature_evidence: List[Dict[str, str]] = []
    selection_reason = ""
    best_answer = base_wrong_answer
    dialect_passed = False
    dialect_reason = "The dialect rewrite was not validated."

    for _ in range(max_retries):
        prompt = build_dialect_speaker_prompt(
            dialect_type=dialect_type,
            question=question_text,
            base_wrong_answer=base_wrong_answer,
        )
        obj, _, _ = query_corruption_json_llm(
            sys_prompt=prompt,
            user_prompt="",
            temperature=0.5,
        )

        applicable = _as_bool(obj.get("applicable"))
        applicability_reason = str(obj.get("applicability_reason", "")).strip()
        applied_features = _normalize_features(obj.get("applied_features"))
        feature_evidence = _normalize_evidence(obj.get("feature_evidence"))
        selection_reason = str(obj.get("selection_reason", "")).strip()
        candidate = str(obj.get("updated_text", base_wrong_answer)).strip()

        if not applicable:
            best_answer = base_wrong_answer
            applied_features = []
            feature_evidence = []
            dialect_passed = True
            dialect_reason = "Not applicable: " + applicability_reason
            break

        best_answer = candidate
        if not applied_features:
            dialect_reason = "No applied dialect features were returned."
            continue
        # Let the dialect validator assess the claimed features and evidence.

        dialect_passed, dialect_reason = _validate_dialect_speaker_rewrite(
            dialect_type=dialect_type,
            base_wrong_answer=base_wrong_answer,
            updated_wrong_answer=candidate,
            feature_evidence=feature_evidence,
        )
        if dialect_passed:
            break

    incorrect_passed, _, incorrect_reason = validate_incorrectness(
        question_text,
        best_answer,
    )

    return DialectSpeakerCorruptionRecord(
        session_id=session_id,
        question_turn_index=question_turn_index,
        question_turn_number=question_turn_number,
        dialect_type=dialect_type,
        phenomenon_type=dialect_type,
        applicable=applicable,
        applicability_reason=applicability_reason,
        applied_features=applied_features,
        feature_evidence=feature_evidence,
        num_added_words=max(
            count_words(best_answer) - count_words(base_wrong_answer), 0
        ),
        selected_item=", ".join(applied_features),
        selected_items=applied_features,
        num_instances=len(feature_evidence),
        selection_reason=selection_reason,
        base_wrong_answer=base_wrong_answer,
        updated_wrong_answer=best_answer,
        selected_item_validator_passed=dialect_passed,
        selected_item_validator_reason=dialect_reason,
        answer_eval="INCORRECT" if incorrect_passed else "CORRECT",
        incorrect_validator_passed=incorrect_passed,
        incorrect_validator_reason=incorrect_reason,
    )
