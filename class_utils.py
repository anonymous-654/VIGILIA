from typing import List, Dict, Any

from llm_api import query_llm
from prompts import PLANNER_PROMPT, SPEAKER_PROMPT, EXTRACTOR_PROMPT
from utils import parse_json_string, safe_json_from_llm


def format_full_history(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "(no prior dialogue yet)"
    return "\n".join(
        f"Turn {x['turn']} | Speaker: {x['speaker']} | Action: {x['action']} | Segment: {x['segment']} | Utterance: {x['utterance']}"
        for x in history
    )


def format_speaker_history(history: List[Dict[str, Any]]) -> str:
    if not history:
        return "(no prior dialogue yet)"
    return "\n".join(f"{x['speaker']}: {x['utterance']}" for x in history)


def prompt_planner(
        model_path:str, history_string: str, subject:str, topic:str, students:List, 
        lesson_segments:List, last_segment_index:int=0, last_action:str=None, user_prompt: str = ""):
    planner_prompt = PLANNER_PROMPT.format(
        SUBJECT_PLACEHOLDER=subject,
        TOPIC_PLACEHOLDER=topic,
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        SEGMENT_LIST="\n".join(f"- [{i}] {title}" for i, title in enumerate(lesson_segments)),
        HISTORY_PLACEHOLDER=history_string if history_string.strip() else "(no prior dialogue yet)",
        LAST_SEGMENT_INDEX=last_segment_index,
        LAST_ACTION=last_action,
    )

    raw_response, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=planner_prompt,
        user_prompt=user_prompt,
    )

    # print(raw_response)

    teacher_json = parse_json_string(raw_response)

    # prefix utterance for logging
    if "utterance" in teacher_json:
        teacher_json["utterance"] = teacher_json["utterance"].strip()

    return teacher_json, pt, ct

def prompt_speaker(
    model_path:str,history_string: str, subject:str, topic:str, students:List, lesson_segments:List, 
    segment_index:int=0, action:str=None, reason:str = None, user_prompt: str = ""):
    speaker_prompt = SPEAKER_PROMPT.format(
        SUBJECT_PLACEHOLDER=subject,
        TOPIC_PLACEHOLDER=topic,
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        SEGMENT_LIST="\n".join(f"- [{i}] {title}" for i, title in enumerate(lesson_segments)),
        HISTORY_PLACEHOLDER=history_string if history_string.strip() else "(no prior dialogue yet)",
        PLANNED_ACTION=action,
        REASONING=reason,
        PLANNED_SEGMENT_INDEX=segment_index,
    )

    raw_response, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=speaker_prompt,
        user_prompt=user_prompt,
    )

    # print(raw_response)

    teacher_json = parse_json_string(raw_response)

    # prefix utterance for logging
    if "utterance" in teacher_json:
        teacher_json["utterance"] = teacher_json["utterance"].strip()

    return teacher_json, pt, ct

def get_selected_student(model_path:str, utterance:str, students:List):
    """
    Extracts student name from utterance
    """
    prompt = EXTRACTOR_PROMPT.format(
        STUDENT_PLACEHOLDER=", ".join([s["name"] for s in students]),
        UTTERANCE_PLACEHOLDER=utterance
    )
    raw, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=prompt,
        user_prompt=""
    )
    output = parse_json_string(raw)
    print(output)
    selected_student = output["invited_student"] if output["invited_student"] else None
    return selected_student


def generate_lesson_segments(model_path:str, subject:str, topic: str, num_segments: int):
    prompt = f"""
    You are an expert educator and curriculum designer for a {subject} class.

    Your task: break a topic into a clear, logical sequence of lesson segments.

    Requirements:
    - Create exactly {num_segments} segments.
    - Segment titles must be short (3–7 words each).
    - Avoid filler like "Overview" unless meaningful.
    - Order segments logically from basic → advanced.
    - Do NOT explain anything.
    - Output ONLY JSON valid list of strings.

    Topic: "{topic}
    """

    raw, _, _ = query_llm(model_path, prompt)
    print(raw)
    segments = safe_json_from_llm(raw)
    segments = segments + ["Conclusion"]
    return segments
