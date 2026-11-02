from typing import Any, Dict, List


def format_dialogue_only(conversation_history: List[Dict[str, Any]]) -> str:
    return "\n".join(f'{h["speaker"]}: {h["utterance"]}' for h in conversation_history)


def format_turn_history(conversation_history: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f'{h["speaker"]} ({h["action"]}, segment {h["segment"]}): {h["utterance"]}'
        for h in conversation_history
    )
