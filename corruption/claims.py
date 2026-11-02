from typing import List

from llm.client import query_small_json_llm
from corruption.prompts import CLAIM_EXTRACTION_PROMPT
from schemas import ClaimUnit


def extract_claims(question: str, gold_answer: str) -> List[ClaimUnit]:
    prompt = CLAIM_EXTRACTION_PROMPT.format(QUESTION=question, GOLD_ANSWER=gold_answer)
    obj, _, _ = query_small_json_llm(sys_prompt=prompt, user_prompt="")
    return [ClaimUnit(**c) for c in obj["claims"]]
