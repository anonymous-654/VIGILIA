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


LANGUAGE_PHENOMENON_CORRUPTION_PROMPT = """
You are modifying a response (an already wrong student answer to a question) to exhibit a specific linguistic phenomenon while preserving its original meaning.

Question: {QUESTION}

Original text:
{BASE_WRONG_ANSWER}

Phenomenon type:
{PHENOMENON_TYPE}_language

Phenomenon description:
{PHENOMENON_DESCRIPTION}

Allowed phenomenon items:
{PHENOMENON_ITEMS}

Injection degree:
{DEGREE}

Degree controls how strongly the phenomenon should appear:

- Degree 1:
  - Introduce exactly 1 phenomenon item.
  - Make the smallest possible edit.
  - The phenomenon should be clearly noticeable while keeping the text fluent and natural.

- Degree 2:
  - Introduce up to 2 phenomenon items.
  - Prefer 2 items when they can be integrated naturally.
  - Distribute them naturally across the response.
  - The phenomenon should be clearly noticeable while keeping the text fluent and natural.

- Degree 3:
  - Introduce up to 3 phenomenon items.
  - Prefer 3 items when they can be integrated naturally.
  - Distribute them naturally across the response.
  - The phenomenon should be clearly noticeable while keeping the text fluent and natural.

IMPORTANT:
Naturalness, coherence, and answer plausibility take priority over reaching the target number of items.

For very short answers (e.g., a single word, short phrase, number, formula, unit, or entity name):
  - Do not force multiple phenomenon items if doing so would create an unnatural or incoherent response.
  - Use the maximum number of phenomenon items that can be inserted naturally.
  - It is acceptable to use fewer than the target number of items.
  - Report the actual number used in num_instances.

Requirements:
1. Preserve the original meaning, content, intent, and answer structure.
2. Do NOT add new information.
3. Do NOT remove important information.
4. Integrate the selected items naturally into the text.
5. The phenomenon items must serve a genuine linguistic function, not appear as random insertions.
6. Keep the response coherent, grammatical, and plausible.
7. Prefer minimal edits consistent with the requested degree.
8. Use only items from the allowed list.
9. The resulting text should still read as something a human would naturally write.
10. The resulting text must remain a plausible response to the given question.

Return STRICT JSON only:

{{
  "selected_items": ["item1", "item2"],
  "num_instances": 2,
  "selection_reason": "Brief explanation of why these items were chosen and how they realize the phenomenon.",
  "updated_text": "The modified response."
}}
"""
