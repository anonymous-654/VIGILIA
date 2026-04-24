ERROR_SELECTION_PROMPT = """
You are designing a hard-to-detect but still clearly incorrect student answer.

Question: {QUESTION}
Gold answer: {GOLD_ANSWER}
Claims:
{CLAIMS}

Allowed error types:
- entity_swap
- causal_reversal
- definition_confusion
- overgeneralization
- fabricated_mechanism
- quantitative_misstatement
- generic_false_claim

Task:
Choose the single best claim and single best error type that would create a plausible wrong answer that is difficult for a teacher to detect quickly in conversation.

Return STRICT JSON only:
{{
  "selected_claim_id": "...",
  "selected_error_type": "...",
  "reason": "..."
}}
"""

CLAIM_EXTRACTION_PROMPT = """
Break the gold answer into atomic factual claims.

Question: {QUESTION}
Gold answer: {GOLD_ANSWER}

Return STRICT JSON only:
{{
  "claims": [
    {{
      "claim_id": "c1",
      "claim_text": "...",
      "claim_role": "definition|mechanism|cause|effect|quantity|comparison|other"
    }}
  ]
}}
"""

BASE_CORRUPTION_PROMPT = """
You are generating a controlled semantic corruption.

Question: {QUESTION}
Gold answer: {GOLD_ANSWER}
Claims:
{CLAIMS}
Selected claim id: {SELECTED_CLAIM_ID}
Selected claim text: {SELECTED_CLAIM_TEXT}
Selected error type: {SELECTED_ERROR_TYPE}

Requirements:
- Keep the answer natural.
- Keep overall answer format similar to the gold answer.
- Modify the selected claim so the full answer becomes incorrect.
- Change as little else as possible.
- Do not make the answer absurd.

Return STRICT JSON only:
{{
  "corrupted_claim_text": "...",
  "base_wrong_answer": "..."
}}
"""

STYLE_CORRUPTION_PROMPT = """
You are applying a persuasion style to an already wrong answer.

Question: {QUESTION}
Base wrong answer: {BASE_WRONG_ANSWER}
Style: {STYLE_TYPE}

Rules by style:
- plain: keep it natural and straightforward
- credibility: add vague expert/institution/research cues without real citations
- emotion: add emotional urgency, value-laden framing, or fear/empathy cues
- anecdote: support with personal experience, hearsay, or anecdotal phrasing

Requirements:
- Preserve the same underlying wrong content.
- Do not repair the answer.
- Keep length roughly similar.
- Keep it plausible.

Return STRICT JSON only:
{{
  "styled_wrong_answer": "..."
}}
"""