import random
import uuid
from typing import Dict, List
from core.history import format_dialogue_only, format_turn_history
from llm.classroom import (
    generate_lesson_segments,
    get_selected_student,
    prompt_planner,
    prompt_speaker,
)
from llm.client import query_small_llm
from llm.classroom_prompts import STUDENT_QUESTION_PROMPT, STUDENT_ANSWER_PROMPT
from schemas import SessionRecord

student_prompt = STUDENT_QUESTION_PROMPT
student_answer_sys_prompt = STUDENT_ANSWER_PROMPT


def sample_random_hand_raisers(students: List[Dict], num_raisers: int) -> List[str]:
    student_names = [student["name"] for student in students]
    if not student_names:
        return []
    return random.sample(student_names, k=min(num_raisers, len(student_names)))


def run_class_session(
    students: List[Dict],
    model_path: str,
    subject: str,
    topic: str,
    num_raisers=2,
    max_turns: int = 200,
):

    session_id = str(uuid.uuid4())

    num_segments = random.choice([5, 6, 7])
    lesson_segments = generate_lesson_segments(model_path, subject, topic, num_segments)

    conversation_history = []
    reason = ""
    segment_index = 0
    num_questions = 0
    tpt, tct = 0, 0
    last_segment_index = 0
    last_action = None
    has_started = False

    last_hand_raisers = []

    selected_speakers = []
    all_hand_raises = []
    selected_speaker_indices = []
    questions_asked = []

    turns_ran = 0

    for turn in range(max_turns):
        turns_ran += 1

        history_string = format_turn_history(conversation_history)
        speaker_history_string = format_dialogue_only(conversation_history)

        if not has_started:
            action = "StartLecture"
            has_started = True
            seg_idx = 0
        else:
            # ---------- 0) PLANNER DECISION ----------
            planner_json, pt, ct = prompt_planner(
                model_path=model_path,
                history_string=history_string,
                subject=subject,
                topic=topic,
                students=students,
                lesson_segments=lesson_segments,
                last_segment_index=last_segment_index,
                last_action=last_action,
                user_prompt="",
            )
            tpt += pt
            tct += ct
            action = planner_json["next_action"]
            seg_idx = planner_json["next_segment_index"]
            reason = planner_json["reasoning"]

        # ---------- 0) SPEAKER Utterance ----------
        speaker_json, pt, ct = prompt_speaker(
            model_path=model_path,
            history_string=speaker_history_string,
            subject=subject,
            topic=topic,
            students=students,
            lesson_segments=lesson_segments,
            segment_index=seg_idx,
            action=action,
            reason=reason,
            user_prompt="",
        )

        tpt += pt
        tct += ct
        utterance = speaker_json["utterance"]

        last_segment_index = seg_idx

        # Ensure valid segment index
        if 0 <= seg_idx < len(lesson_segments):
            segment_index = seg_idx

        # Log teacher utterance
        conversation_history.append(
            {
                "turn": turn,
                "speaker": "Teacher",
                "action": action,
                "segment": segment_index,
                "utterance": utterance,
            }
        )

        if action == "EndLecture":
            break

        # ---------- 2) HANDLE ACTIONS ----------

        # A. Teacher asks class a question → simulate hand raises
        if action == "AskQuestion":

            num_questions += 1
            asked_question = utterance
            questions_asked.append(asked_question)

            # hand raise
            hand_raisers = sample_random_hand_raisers(students, num_raisers=num_raisers)
            last_hand_raisers = list(hand_raisers)
            all_hand_raises.append(last_hand_raisers)
            conversation_history.append(
                {
                    "turn": turn,
                    "speaker": ", ".join(hand_raisers),
                    "action": "RaiseHand",
                    "segment": segment_index,
                    "utterance": "(raise hands to answer)",
                }
            )
            last_action = action
            continue

        # B. Teacher invites one student to answer
        if action == "InviteStudentAnswer":
            selected_student = get_selected_student(model_path, utterance, students)
            student_names = [s["name"] for s in students]
            if selected_student and selected_student in last_hand_raisers:
                answering_student = selected_student
            elif last_hand_raisers:
                answering_student = random.choice(last_hand_raisers)
            elif selected_student and selected_student in student_names:
                answering_student = selected_student
            else:
                answering_student = random.choice(student_names)

            selected_speakers.append(answering_student)
            selected_speaker_indices.append(
                last_hand_raisers.index(answering_student)
                if answering_student in last_hand_raisers
                else None
            )

            student_answer_prompt_filled = student_answer_sys_prompt.format(
                name=answering_student,
                SUBJECT_PLACEHOLDER=subject,
                TOPIC_PLACEHOLDER=topic,
                HISTORY_PLACEHOLDER=speaker_history_string,
            )

            student_answer, spt, sct = query_small_llm(
                sys_prompt=student_answer_prompt_filled, user_prompt=""
            )

            conversation_history.append(
                {
                    "turn": turn,
                    "speaker": answering_student,
                    "action": "Answer",
                    "segment": segment_index,
                    "utterance": student_answer.strip(),
                }
            )

            tpt += spt
            tct += sct

            last_action = action
            continue

        # C. Teacher invites students to ask questions
        if action == "InviteStudentQuestion":
            # simulate a hand raise
            asker = random.choice([s["name"] for s in students])
            conversation_history.append(
                {
                    "turn": turn,
                    "speaker": asker,
                    "action": "RaiseHand",
                    "segment": segment_index,
                    "utterance": "(raises hand to ask a question)",
                }
            )

            student_question_prompt_filled = student_prompt.format(
                name=asker,
                SUBJECT_PLACEHOLDER=subject,
                TOPIC_PLACEHOLDER=topic,
                HISTORY_PLACEHOLDER=speaker_history_string,
            )
            student_question, spt, sct = query_small_llm(
                sys_prompt=student_question_prompt_filled, user_prompt=""
            )
            conversation_history.append(
                {
                    "turn": turn,
                    "speaker": asker,
                    "action": "AskQuestion",
                    "segment": segment_index,
                    "utterance": student_question.strip(),
                }
            )

            tpt += spt
            tct += sct
            last_action = action
            continue

        # D. Teacher answers a student question
        if action == "AnswerQuestion":
            # No extra control here — teacher output already logged
            last_action = action
            continue

        # E. ContinueLecture / StartLecture do nothing special here
        if action in {"StartLecture", "ContinueLecture"}:
            last_action = action
            continue

    return SessionRecord(
        session_id=session_id,
        subject=subject,
        topic=topic,
        lesson_segments=lesson_segments,
        students=students,
        conversation_history=conversation_history,
        selected_speakers=selected_speakers,
        selected_speaker_indices=selected_speaker_indices,
        all_hand_raises=all_hand_raises,
        num_questions=num_questions,
        questions_asked=questions_asked,
        turns_ran=turns_ran,
        prompt_tokens=tpt,
        completion_tokens=tct,
        metadata={},
    )
