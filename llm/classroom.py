from typing import List

from llm.client import query_json_llm, query_small_json_llm
from llm.classroom_prompts import (
    LESSON_SEGMENTS_PROMPT,
    PLANNER_PROMPT,
    SPEAKER_PROMPT,
    STUDENT_EXTRACTOR_PROMPT,
)


def prompt_planner(
    model_path: str,
    history_string: str,
    subject: str,
    topic: str,
    students: List,
    lesson_segments: List,
    last_segment_index: int = 0,
    last_action: str = None,
    user_prompt: str = "",
):
    planner_prompt = PLANNER_PROMPT.format(
        SUBJECT_PLACEHOLDER=subject,
        TOPIC_PLACEHOLDER=topic,
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        SEGMENT_LIST="\n".join(
            f"- [{i}] {title}" for i, title in enumerate(lesson_segments)
        ),
        HISTORY_PLACEHOLDER=(
            history_string if history_string.strip() else "(no prior dialogue yet)"
        ),
        LAST_SEGMENT_INDEX=last_segment_index,
        LAST_ACTION=last_action,
    )

    teacher_json, pt, ct = query_json_llm(
        model_path=model_path,
        sys_prompt=planner_prompt,
        user_prompt=user_prompt,
    )

    if "utterance" in teacher_json:
        teacher_json["utterance"] = teacher_json["utterance"].strip()

    return teacher_json, pt, ct


def prompt_speaker(
    model_path: str,
    history_string: str,
    subject: str,
    topic: str,
    students: List,
    lesson_segments: List,
    segment_index: int = 0,
    action: str = None,
    reason: str = None,
    user_prompt: str = "",
):
    speaker_prompt = SPEAKER_PROMPT.format(
        SUBJECT_PLACEHOLDER=subject,
        TOPIC_PLACEHOLDER=topic,
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        SEGMENT_LIST="\n".join(
            f"- [{i}] {title}" for i, title in enumerate(lesson_segments)
        ),
        HISTORY_PLACEHOLDER=(
            history_string if history_string.strip() else "(no prior dialogue yet)"
        ),
        PLANNED_ACTION=action,
        REASONING=reason,
        PLANNED_SEGMENT_INDEX=segment_index,
    )

    teacher_json, pt, ct = query_json_llm(
        model_path=model_path,
        sys_prompt=speaker_prompt,
        user_prompt=user_prompt,
    )

    if "utterance" in teacher_json:
        teacher_json["utterance"] = teacher_json["utterance"].strip()

    return teacher_json, pt, ct


def get_selected_student(model_path: str, utterance: str, students: List):
    prompt = STUDENT_EXTRACTOR_PROMPT.format(
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        UTTERANCE_PLACEHOLDER=utterance,
    )
    output, _, _ = query_small_json_llm(
        sys_prompt=prompt,
        user_prompt="",
    )
    return output["invited_student"] if output["invited_student"] else None


def generate_lesson_segments(
    model_path: str, subject: str, topic: str, num_segments: int
):
    prompt = LESSON_SEGMENTS_PROMPT.format(
        subject=subject,
        topic=topic,
        num_segments=num_segments,
    )
    segments, _, _ = query_small_json_llm(sys_prompt=prompt)
    return segments + ["Conclusion"]
