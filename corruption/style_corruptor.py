import json
from enums import AttackType
from llm_api import query_small_llm
from corruption.prompts import STYLE_CORRUPTION_PROMPT
from schemas import StyledCorruptionRecord
from corruption.validators import validate_incorrectness, validate_style


def apply_style_corruption(
    model_path: str,
    session_id: str,
    question_turn_index: int,
    question_turn_number: int,
    question_text: str,
    base_wrong_answer: str,
    style_type: str,
    max_retries: int = 3,
) -> StyledCorruptionRecord:
    best_answer = base_wrong_answer
    style_passed = False
    style_reason = ""
    incorrect_passed = False
    incorrect_reason = ""

    if style_type == AttackType.PLAIN.value:
        # For plain style, we skip the style transformation and directly validate the base wrong answer.
        best_answer = base_wrong_answer
        style_passed = True  # No style to validate for plain attack
        style_reason = "No style transformation for plain attack."
        incorrect_passed, _, incorrect_reason = validate_incorrectness(question_text, best_answer)
        return StyledCorruptionRecord(
            session_id=session_id,
            question_turn_index=question_turn_index,
            question_turn_number=question_turn_number,
            style_type=style_type,
            base_wrong_answer=base_wrong_answer,
            styled_wrong_answer=best_answer,
            style_validator_passed=style_passed,
            style_validator_reason=style_reason,
            incorrect_validator_passed=incorrect_passed,
            incorrect_validator_reason=incorrect_reason,
            answer_eval = "INCORRECT" if incorrect_passed else "CORRECT"
        )

    for _ in range(max_retries):
        prompt = STYLE_CORRUPTION_PROMPT.format(
            QUESTION=question_text,
            BASE_WRONG_ANSWER=base_wrong_answer,
            STYLE_TYPE=style_type,
        )
        # raw, _, _ = query_small_llm(model_path=model_path, sys_prompt=prompt, user_prompt="", temperature=0.5)
        raw, _, _ = query_small_llm(sys_prompt=prompt, user_prompt="", temperature=0.5)
        obj = json.loads(raw)
        candidate = obj["styled_wrong_answer"].strip()

        style_passed, style_reason = validate_style(candidate, style_type)
        incorrect_passed, _, incorrect_reason = validate_incorrectness(question_text, candidate)
        best_answer = candidate

        if style_passed and incorrect_passed:
            break

    return StyledCorruptionRecord(
        session_id=session_id,
        question_turn_index=question_turn_index,
        question_turn_number=question_turn_number,
        style_type=style_type,
        base_wrong_answer=base_wrong_answer,
        styled_wrong_answer=best_answer,
        style_validator_passed=style_passed,
        style_validator_reason=style_reason,
        incorrect_validator_passed=incorrect_passed,
        incorrect_validator_reason=incorrect_reason,
        answer_eval = "INCORRECT" if incorrect_passed else "CORRECT"
    )