"""Linguistic conditions and their bundled category vocabulary."""

import json
from pathlib import Path

with (
    Path(__file__)
    .with_name("liwc_categories_exclusive.json")
    .open(encoding="utf-8") as handle
):
    liwc_cats = json.load(handle)

hedge_verb_phrases = [
    "I think",
    "I guess",
    "I suppose",
    "I believe",
    "I imagine",
    "I suspect",
    "I reckon",
    "I feel",
    "I assume",
    "I wonder",
    "I would say",
    "I tend to think",
    "it seems",
    "it appears",
    "my understanding is",
    "if I remember correctly",
]


LANGUAGE_PHENOMENA = {
    "tentative": liwc_cats["TENTAT"],
    "certainty": liwc_cats["CERTAIN"],
    "insight": liwc_cats["INSIGHT"],
    "discrepancy": liwc_cats["DISCREP"],
    "hedge_verb_phrases": hedge_verb_phrases,
}

LANGUAGE_PHENOMENON_DESCRIPTIONS = {
    "tentative": (
        "Express uncertainty, possibility, approximation, ambiguity, or lack of "
        "commitment. Use language that presents information as provisional, "
        "speculative, approximate, or not fully known."
    ),
    "certainty": (
        "Express confidence, definiteness, necessity, truth, or conviction. "
        "Use language that presents claims as established, precise, undeniable, "
        "or highly certain."
    ),
    "insight": (
        "Express cognitive processing, understanding, reasoning, realization, "
        "interpretation, learning, or reflection. Use language that signals "
        "thinking about, explaining, understanding, discovering, remembering, "
        "or making sense of information."
    ),
    "discrepancy": (
        "Express a difference between actual and desired, expected, intended, "
        "required, or possible states of affairs. Use language involving wants, "
        "needs, obligations, expectations, hypotheticals, or alternative "
        "outcomes such as 'should', 'would', 'could', 'want', 'wish', or 'hope'."
    ),
    "hedge_verb_phrases": (
        "Express epistemic uncertainty or soften assertions through first-person "
        "cognitive or perceptual verb phrases such as 'I think', 'I guess', "
        "'I suppose', 'I wonder', or similar constructions."
    ),
}


DEFAULT_LANGUAGE_PHENOMENA = list(LANGUAGE_PHENOMENA.keys())


def format_phenomenon_items(phenomenon_type: str) -> str:
    items = LANGUAGE_PHENOMENA[phenomenon_type]
    return "\n".join(f"- {item}" for item in items)
