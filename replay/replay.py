import copy
import random
import json
import re
from typing import Dict, List, Optional, Tuple

from llm_api import query_small_llm
from llm_utils import get_selected_student
from vigilance.teacher_followup import generate_teacher_followup
from vigilance.profile_groups import PROFILE_GROUPS, aggregate_all_names


ALL_KNOWN_NAMES = aggregate_all_names()

NAME_RE = re.compile(
    r"\b(" + "|".join(map(re.escape, sorted(ALL_KNOWN_NAMES, key=len, reverse=True))) + r")\b"
)


def replace_names_in_utterance(utterance: str, replacement_name: str) -> str:
    return NAME_RE.sub(replacement_name, utterance)


def attach_profile_variant(session_dict: Dict, new_students: List[Dict], target_profile_type: str) -> Dict:
    updated = copy.deepcopy(session_dict)
    updated["students"] = copy.deepcopy(new_students)
    updated.setdefault("metadata", {})
    updated["metadata"]["target_profile_type"] = target_profile_type
    updated["metadata"]["source_session_id"] = session_dict.get("session_id")
    return updated

def _safe_json_load(raw: str):
    return json.loads(raw)


def resimulate_hand_raisers(
    students: List[Dict],
    num_raisers: int,
    profile_type: str,
    target_group: str = None,
) -> List[str]:
    student_names = [s["name"] for s in students]
    if target_group is not None:
        allowed_names = set(PROFILE_GROUPS[profile_type][target_group])
        student_names = [n for n in student_names if n in allowed_names]
        return random.sample(student_names, min(num_raisers, len(student_names)))
    else:
        return random.sample(student_names, min(num_raisers, len(student_names)))

def replay_session_with_new_roster(
    session_dict: Dict,
    new_students: List[Dict],
    target_profile_type: str,
    target_group: str,
    model_path: str,
    num_raisers: int = 2,
) -> Dict:
    """
    Replay the class under a new roster.

    Keep:
    - teacher lecture content
    - original answer text

    Resimulate:
    - hand raisers
    - invited student
    - answer attribution
    """
    updated = attach_profile_variant(session_dict, new_students, target_profile_type)

    old_history = session_dict["conversation_history"]
    new_history = []

    current_raisers: List[str] = []
    last_question_text: Optional[str] = None
    last_selected_student: Optional[str] = None

    selected_speakers = []
    all_hand_raises = []
    selected_speaker_indices = []

    prev_speaker = None
    asker = None

    for event in old_history:
        speaker = event.get("speaker")
        action = event.get("action")

        # keep teacher lecture flow fixed
        if speaker == "Teacher" and action in {"StartLecture", "ContinueLecture", "AskQuestion", "AnswerQuestion", "EndLecture", "InviteStudentQuestion"}:
            new_event = copy.deepcopy(event)
            if (last_selected_student is not None
                and (
                    (prev_speaker is not None and prev_speaker != "Teacher")  # Student -> Teacher transition
                    or action == "EndLecture"  # Always update EndLecture
                    )
                    ):
                new_event["utterance"] = replace_names_in_utterance(
                    new_event.get("utterance", ""),
                    last_selected_student,
                )

            new_history.append(new_event)

            if action == "AskQuestion":
                last_question_text = event.get("utterance", "")
                current_raisers = resimulate_hand_raisers(
                    students=new_students,
                    num_raisers=num_raisers,
                    profile_type=target_profile_type,
                    target_group=target_group,
                )
                new_history.append(
                    {
                        "turn": event["turn"],
                        "speaker": ", ".join(current_raisers),
                        "action": "RaiseHand",
                        "segment": event.get("segment", 0),
                        "utterance": "(raise hands to answer)",
                    }
                )
                all_hand_raises.append(current_raisers)

            
            # change student asker if teacher invited a question
            if action == "InviteStudentQuestion":
                # simulate a hand raise
                asker = random.choice([s["name"] for s in new_students])
                new_history.append(
                    {"turn": event["turn"], 
                        "speaker": asker, 
                        "action": "RaiseHand", 
                        "segment": event.get("segment", 0), 
                        "utterance": "(raises hand to ask a question)"})
                
            prev_speaker = speaker
            continue


        # skip original raise-hand events because they are resimulated
        if action == "RaiseHand":
            prev_speaker = None
            continue

        # replace teacher invitation to match new selected student
        if speaker == "Teacher" and action == "InviteStudentAnswer":
            # change the teacher utterance to invite the newly selected student
            action, utterance = generate_teacher_followup(
                model_path=model_path,
                subject=session_dict.get("subject", ""),
                topic=session_dict.get("topic", ""),
                students=new_students,
                lesson_segments=session_dict.get("lesson_segments", []),
                counterfactual_history=new_history,
                segment_index=event.get("segment", 0),
            )

            if current_raisers:
                last_selected_student = get_selected_student(model_path, utterance, new_students)
            else:
                last_selected_student = new_students[0]["name"]

            selected_speakers.append(last_selected_student)

            # Only log index if the selected student was actually in the most recent hand-raisers.
            if current_raisers and (last_selected_student in current_raisers):
                try:
                    idx = current_raisers.index(last_selected_student)  # index inside the hand-raiser list
                except ValueError:
                    idx = None
            else:
                idx = None
            selected_speaker_indices.append(idx)     # append index or None

            new_event = copy.deepcopy(event)
            # new_event["utterance"] = f"{last_selected_student}, go ahead."
            new_event["utterance"] = utterance
            new_history.append(new_event)
            prev_speaker = speaker
            continue

        # keep same answer text, change speaker to selected student
        if action == "Answer" and speaker != "Teacher":
            new_event = copy.deepcopy(event)
            if last_selected_student is not None:
                new_event["speaker"] = last_selected_student
            new_history.append(new_event)
            prev_speaker = speaker
            continue

        # for student question. Chnage the speaker to the asker, but keep the question text the same
        if action == "AskQuestion":
            new_event = copy.deepcopy(event)
            if speaker != "Teacher":
                if asker is not None:
                    new_event["speaker"] = asker
            new_history.append(new_event)
            prev_speaker = speaker
            continue

        # for student questions, keep as-is for now
        # for others, keep as-is for now
        new_history.append(copy.deepcopy(event))
        prev_speaker = speaker

    updated["conversation_history"] = new_history
    updated["all_hand_raises"] = all_hand_raises
    updated["selected_speakers"] = selected_speakers
    updated["selected_speaker_indices"] = selected_speaker_indices
    updated.setdefault("metadata", {})
    updated["metadata"]["replay_mode"] = "participation_resimulated"
    updated["metadata"]["teacher_structure_fixed"] = True
    return updated