import time
from openai import APIError
from typing import Dict, List, Tuple

from llm.classroom import prompt_planner, prompt_speaker
from core.history import format_dialogue_only, format_turn_history


REQUIRED_PLANNER_KEYS = ("next_action", "next_segment_index", "reasoning")
REQUIRED_SPEAKER_KEYS = ("utterance",)


def _require_keys(obj: Dict, required_keys, label: str) -> None:
    missing = [key for key in required_keys if key not in obj]
    if missing:
        raise KeyError(f"{label} response missing keys {missing}: {obj}")


def build_counterfactual_history(
    history: List[Dict], answer_idx: int, wrong_answer: str
) -> List[Dict]:
    cf_history = [dict(x) for x in history[: answer_idx + 1]]
    cf_history[answer_idx]["utterance"] = wrong_answer
    return cf_history


def generate_teacher_followup(
    model_path: str,
    subject: str,
    topic: str,
    students: List[Dict],
    lesson_segments: List[str],
    counterfactual_history: List[Dict],
    segment_index: int,
    max_attempts: int = 2,
    log_context: str = "",
) -> Tuple[str, str]:
    history_string = format_turn_history(counterfactual_history)
    speaker_history = format_dialogue_only(counterfactual_history)

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            planner_json, _, _ = prompt_planner(
                model_path=model_path,
                history_string=history_string,
                subject=subject,
                topic=topic,
                students=students,
                lesson_segments=lesson_segments,
                last_segment_index=segment_index,
                last_action="InviteStudentAnswer",
            )
            _require_keys(planner_json, REQUIRED_PLANNER_KEYS, "planner")

            action = planner_json["next_action"]
            seg_idx = planner_json["next_segment_index"]
            reason = planner_json["reasoning"]

            speaker_json, _, _ = prompt_speaker(
                model_path=model_path,
                history_string=speaker_history,
                subject=subject,
                topic=topic,
                students=students,
                lesson_segments=lesson_segments,
                segment_index=seg_idx,
                action=action,
                reason=reason,
            )
            _require_keys(speaker_json, REQUIRED_SPEAKER_KEYS, "speaker")

            return action, speaker_json["utterance"].strip()
        except APIError:
            # Transport/API retries are owned by the client; do not multiply them here.
            raise
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            print(
                f"[WARN] Teacher followup generation failed attempt={attempt}/{max_attempts}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            time.sleep(2 * attempt)

    raise ValueError(
        f"Teacher followup generation did not return required fields after {max_attempts} attempts."
    ) from last_error
