import re


def extract_response_from_local_llm(text: str) -> str:
    """
    Remove local model thinking blocks and return only the final response text.
    """
    if text is None:
        raise ValueError("extract_response_from_local_llm got None")
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()
