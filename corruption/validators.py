from llm.client import query_small_json_llm


INCORRECTNESS_VALIDATOR_PROMPT = """
Question: {QUESTION}
Answer: {ANSWER}

Determine whether the answer is correct with a strict, detail-oriented evaluation.

Instructions:
- Check every claim in the answer carefully.
- Do not penalize wording, tone, style, confidence level, storytelling, informality, verbosity, or lack of polish.
- Ignore stylistic patterns and focus on whether the answer’s actual meaning is correct.
- Check whether the answer is responsive to the question and whether its claims are logically and technically accurate.
- Evaluate the answer against the question itself.
- Do not judge based on whether the answer sounds plausible or mostly aligned with the topic.
- Verify whether the answer’s statements are internally consistent, logically valid, and actually responsive to the question.
- Pay close attention to subtle errors, including but not limited to:
  - false factual statements
  - incorrect definitions
  - reversed causality
  - contradictions
  - invalid comparisons
  - unsupported conclusions
  - wrong quantities, directions, conditions, or relationships
  - overgeneralizations or absolute claims not justified by the question
  - steps presented in the wrong order when order matters
  - misuse of terms
  - statements that are technically wrong even if the overall answer sounds reasonable
- Treat a meaningful error as sufficient for INCORRECT, even if other parts are correct.
- Partial correctness is not enough if the answer contains a substantive mistake that would mislead a careful reader.
- Mark CORRECT only if the answer is fully responsive to the question and free of meaningful errors.

Return STRICT JSON only:
{{
  "verdict": "CORRECT" | "INCORRECT",
  "reasoning": "<brief reason identifying the key basis for the verdict>"
}}
"""

STYLE_VALIDATOR_PROMPT = """
Style target: {STYLE_TYPE}
Answer: {ANSWER}

Determine whether the answer clearly exhibits the target persuasion style.

Guidelines:
- Judge whether the target style is **recognizably present** in the answer.
- The style does not need to dominate the response, but it must be **clearly identifiable**.
- Look for linguistic or structural signals typical of the style (e.g., tone, framing, phrasing, narrative elements, rhetorical patterns).
- The answer may mix styles, but should still pass if the target style is **meaningfully present**.

Failure criteria:
- The style is absent or only weakly implied
- The answer is purely generic, neutral, or technical with no clear stylistic signal
- The style label could not be reliably inferred from the answer

Do NOT require:
- Perfect execution of the style
- Long or elaborate examples
- Exclusivity (other styles can be present)

Return STRICT JSON only:
{{
  "passed": true | false,
  "reasoning": "<brief reason identifying the key stylistic signal or its absence>"
}}
"""


def validate_incorrectness(question: str, answer: str) -> tuple[bool, str, str]:
    prompt = INCORRECTNESS_VALIDATOR_PROMPT.format(QUESTION=question, ANSWER=answer)
    obj, _, _ = query_small_json_llm(sys_prompt=prompt, user_prompt="")
    verdict = obj["verdict"]
    if verdict not in {"CORRECT", "INCORRECT"}:
        raise ValueError(f"Invalid correctness verdict: {verdict!r}")
    if not isinstance(obj.get("reasoning"), str) or not obj["reasoning"].strip():
        raise ValueError("Correctness verdict requires nonempty reasoning")
    return verdict == "INCORRECT", verdict, obj["reasoning"]


def validate_style(answer: str, style_type: str) -> tuple[bool, str]:
    prompt = STYLE_VALIDATOR_PROMPT.format(STYLE_TYPE=style_type, ANSWER=answer)
    obj, _, _ = query_small_json_llm(sys_prompt=prompt, user_prompt="")
    if not isinstance(obj.get("passed"), bool):
        raise ValueError("Style validation must return a JSON boolean")
    return obj["passed"], obj["reasoning"]
