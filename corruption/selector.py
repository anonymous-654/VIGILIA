import json
from typing import List, Tuple

from llm_api import query_small_llm
from corruption.prompts import ERROR_SELECTION_PROMPT
from schemas import ClaimUnit


def choose_claim_and_error_type(question: str, gold_answer: str, claims: List[ClaimUnit]) -> Tuple[str, str, str]:
    claims_str = "\n".join([f"- {c.claim_id}: {c.claim_text} ({c.claim_role})" for c in claims])
    prompt = ERROR_SELECTION_PROMPT.format(
        QUESTION=question,
        GOLD_ANSWER=gold_answer,
        CLAIMS=claims_str,
    )
    raw, _, _ = query_small_llm(sys_prompt=prompt, user_prompt="")
    obj = json.loads(raw)
    return obj["selected_claim_id"], obj["selected_error_type"], obj["reason"]