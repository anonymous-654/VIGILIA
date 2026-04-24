from typing import Dict, List, Tuple

from classroom.class_utils import format_full_history, format_speaker_history
from classroom.class_utils import prompt_planner, prompt_speaker


def build_counterfactual_history(history: List[Dict], answer_idx: int, wrong_answer: str) -> List[Dict]:
    cf_history = [dict(x) for x in history[:answer_idx + 1]]
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
) -> Tuple[str, str]:
    history_string = format_full_history(counterfactual_history)
    speaker_history = format_speaker_history(counterfactual_history)

    print(speaker_history)

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

    return action, speaker_json["utterance"].strip()