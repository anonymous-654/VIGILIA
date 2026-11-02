DIALECT_PHENOMENON_CORRUPTION_PROMPT = """
You are minimally editing an already incorrect student answer so that it exhibits
one specified dialect phenomenon.

Question:
{QUESTION}

Original incorrect answer:
{BASE_WRONG_ANSWER}

Dialect phenomenon:
{PHENOMENON_NAME} ({PHENOMENON_TYPE})

Yale Grammatical Diversity Project definition:
{PHENOMENON_DEFINITION}

Application guidance:
{APPLICATION_GUIDANCE}

First decide whether the phenomenon can be introduced naturally while preserving
the answer's existing factual content, incorrect conclusion, polarity, and intent.

If it is applicable:
- Make the smallest grammatical edit that clearly realizes the phenomenon.
- Do not correct the answer or introduce another factual claim.
- Do not imitate an accent with spelling changes.
- Do not add unrelated dialect features.
- Identify the exact span that realizes the phenomenon.
- Copy evidence_span verbatim from updated_text as one contiguous substring.
- Do not add quotation marks around evidence_span unless those quotation marks
  literally occur in updated_text.

If it is not applicable:
- Return the original answer unchanged.
- Explain what grammatical context is missing.

Return STRICT JSON only:
{{
  "applicable": true,
  "applicability_reason": "Why the phenomenon is or is not naturally applicable.",
  "updated_text": "The modified answer, or the unchanged original when inapplicable.",
  "evidence_span": "Exact contiguous text copied verbatim from updated_text, or an empty string.",
  "selection_reason": "Brief explanation of the minimal edit."
}}
"""


DIALECT_PHENOMENON_VALIDATOR_PROMPT = """
Evaluate whether a proposed rewrite correctly realizes a dialect phenomenon while
preserving the original answer's substantive content.

Phenomenon:
{PHENOMENON_NAME} ({PHENOMENON_TYPE})

Definition:
{PHENOMENON_DEFINITION}

Original answer:
{BASE_WRONG_ANSWER}

Proposed rewrite:
{UPDATED_WRONG_ANSWER}

Claimed evidence:
{EVIDENCE_SPAN}

Return STRICT JSON only:
{{
  "phenomenon_present": true,
  "phenomenon_reason": "Brief grammatical justification.",
  "content_preserved": true,
  "content_reason": "Brief comparison of substantive meaning."
}}
"""
