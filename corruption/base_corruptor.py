import json
from typing import List

from llm_api import query_small_llm
from corruption.prompts import BASE_CORRUPTION_PROMPT
from schemas import ClaimUnit, BaseCorruptionRecord
from corruption.validators import validate_incorrectness


def generate_base_corruption(
    model_path: str,
    session_id: str,
    question_turn_index: int,
    question_turn_number: int,
    question_text: str,
    gold_answer: str,
    claims: List[ClaimUnit],
    selected_claim_id: str,
    selected_error_type: str,
    selection_reason: str,
    max_retries: int = 4,
) -> BaseCorruptionRecord:
    claim_map = {c.claim_id: c for c in claims}
    selected_claim = claim_map[selected_claim_id]
    claims_str = "\n".join([f"- {c.claim_id}: {c.claim_text} ({c.claim_role})" for c in claims])

    final_obj = None
    final_verdict = "CORRECT"
    final_reasoning = ""

    for _ in range(max_retries):
        prompt = BASE_CORRUPTION_PROMPT.format(
            QUESTION=question_text,
            GOLD_ANSWER=gold_answer,
            CLAIMS=claims_str,
            SELECTED_CLAIM_ID=selected_claim_id,
            SELECTED_CLAIM_TEXT=selected_claim.claim_text,
            SELECTED_ERROR_TYPE=selected_error_type,
        )
        # raw, _, _ = query_small_llm(model_path=model_path, sys_prompt=prompt, user_prompt="", temperature=0.4)
        raw, _, _ = query_small_llm(sys_prompt=prompt, user_prompt="", temperature=0.4)
        obj = json.loads(raw)
        candidate = obj["base_wrong_answer"].strip()

        is_incorrect, verdict, reasoning = validate_incorrectness(question_text, candidate)
        final_obj = obj
        final_verdict = verdict
        final_reasoning = reasoning
        if is_incorrect:
            break

    return BaseCorruptionRecord(
        session_id=session_id,
        question_turn_index=question_turn_index,
        question_turn_number=question_turn_number,
        question_text=question_text,
        gold_answer=gold_answer,
        selected_claim_id=selected_claim_id,
        selected_claim_text=selected_claim.claim_text,
        selected_error_type=selected_error_type,
        error_selection_reason=selection_reason,
        corrupted_claim_text=final_obj["corrupted_claim_text"],
        base_wrong_answer=final_obj["base_wrong_answer"],
        validator_verdict=final_verdict,
        validator_reasoning=final_reasoning,
    )