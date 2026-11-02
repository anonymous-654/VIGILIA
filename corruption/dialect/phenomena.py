from typing import Dict


DIALECT_PHENOMENA: Dict[str, Dict[str, str]] = {
    "drama_so": {
        "display_name": "Drama SO",
        "yale_url": "https://ygdp.yale.edu/phenomena/drama-so",
        "definition": (
            "Emphatic, typically stressed 'so' can modify expressions that are not "
            "ordinarily gradable. It conveys strong speaker commitment or emphatic "
            "contradiction, as in 'I am SO going' or 'That is so not true.'"
        ),
        "application_guidance": (
            "Use emphatic 'so' where it naturally intensifies the speaker's commitment "
            "to an existing claim. Do not use ordinary degree 'so' before an adjective."
        ),
    },
    "multiple_modals": {
        "display_name": "Multiple modals",
        "yale_url": "https://ygdp.yale.edu/phenomena/multiple-modals",
        "definition": (
            "Two or more modal auxiliaries can occur in one verb phrase, with each "
            "modal contributing meaning, as in 'might could,' 'may can,' or "
            "'might should.'"
        ),
        "application_guidance": (
            "Introduce a natural multiple-modal sequence before an existing predicate. "
            "Preserve the original claim's polarity and avoid adding a new proposition."
        ),
    },
    "invariant_be": {
        "display_name": "Invariant be",
        "yale_url": "https://ygdp.yale.edu/phenomena/invariant-be",
        "definition": (
            "Uninflected 'be' can mark a habitual, recurring, or characteristic state "
            "or event, contrasting with an event or state holding only at the present "
            "moment, as in 'They be working late.'"
        ),
        "application_guidance": (
            "Apply invariant 'be' only when the existing answer can naturally receive "
            "a habitual, recurring, or characteristic interpretation. Do not replace "
            "an ordinary present-tense copula when that would change the meaning."
        ),
    },
    "negative_concord": {
        "display_name": "Negative concord",
        "yale_url": "https://ygdp.yale.edu/phenomena/negative-concord",
        "definition": (
            "Two or more negative forms in the same clause can express a single "
            "semantic negation, as in 'I didn't see nothing.' The negatives agree "
            "rather than canceling one another."
        ),
        "application_guidance": (
            "Apply negative concord only to an already negative claim, adding a "
            "concordant negative indefinite or adverb without reversing polarity."
        ),
    },
    "inversion_in_embedded_questions": {
        "display_name": "Inversion in embedded questions",
        "yale_url": "https://ygdp.yale.edu/phenomena/inversion-embedded-questions",
        "definition": (
            "An embedded interrogative can retain subject-auxiliary inversion, as in "
            "'I wonder where is he' instead of the uninverted 'I wonder where he is.'"
        ),
        "application_guidance": (
            "Apply this only when the answer already contains, or can be minimally "
            "rephrased as, an embedded question without adding information. Invert "
            "the auxiliary and subject inside that embedded question."
        ),
    },
}

DEFAULT_DIALECT_PHENOMENA = list(DIALECT_PHENOMENA.keys())


def get_dialect_phenomenon(phenomenon_type: str) -> Dict[str, str]:
    try:
        return DIALECT_PHENOMENA[phenomenon_type]
    except KeyError as exc:
        choices = ", ".join(sorted(DIALECT_PHENOMENA))
        raise ValueError(
            f"Unknown dialect phenomenon: {phenomenon_type}. Choose one of: {choices}"
        ) from exc
