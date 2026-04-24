import random
from typing import Dict, List
from llm_api import query_llm
from llm_utils import generate_lesson_segments, get_selected_student, prompt_planner, prompt_speaker
from prompts import STU_ANSWER_PROMPT, STU_PROMPT
from utils import format_full_history, format_speaker_history, get_hand_raise, get_parity_list
from vigilance.utils import evaluate_utterance, get_wrong_answer, is_answer_wrong


# intro = """You are **Dr. Anya Sharma**, an expert and passionate Computer Science professor
# specializing in **Large Language Models (LLMs)** and **Natural Language Processing (NLP)**."""
# topic = "Words and Tokens — The Foundation of Large Language Models"

# print(lesson_segments)

student_prompt = STU_PROMPT
student_answer_sys_prompt = STU_ANSWER_PROMPT
#  "credibility" "anecdote" "emotion":
def run_class_session_for_vigilance(students: List[Dict], model_path: str, subject: str, topic:str, profile_type: str, attack_type="credibility"):

    num_segments = random.choice([3, 4, 5])
    # num_segments = 4
    lesson_segments = generate_lesson_segments(model_path, subject, topic, num_segments)
    print(lesson_segments)

    conversation_history = []
    reason = ""
    segment_index = 0
    max_turns = 200

    awaiting_student_answer = False
    awaiting_student_question = False
    num_questions = 0
    tpt, tct = 0,0
    last_segment_index = 0
    last_action = None
    has_started = False
    wrong_answer_given = False

    last_hand_raisers = []

    selected_speakers = []
    all_hand_raises = []
    selected_speaker_indices = []
    questions_asked = []
    num_questions = 0


    num_wrong_answers = 0
    wrong_answers = []
    vigilance_list = []
    answer_evaluations = []

    tpt, tct = 0,0
    turns_ran = 0

    wrong_budget = 3
    is_last_wrong = False
    pending_wrong = None


    for turn in range(max_turns):
        turns_ran += 1

        history_string = format_full_history(conversation_history)
        speaker_history_string = format_speaker_history(conversation_history)

        if not has_started:
            action = "StartLecture"
            has_started = True
            # last_action = action
            seg_idx=0
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
                user_prompt=""
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
            user_prompt=""
        )


        tpt += pt
        tct += ct
        utterance = speaker_json["utterance"]

        last_segment_index = seg_idx

        # Ensure valid segment index
        if 0 <= seg_idx < len(lesson_segments):
            segment_index = seg_idx

        # Log teacher utterance
        print(turn, action, segment_index, reason)
        conversation_history.append({"turn": turn, "speaker": "Teacher","action": action, "segment": segment_index, "utterance": utterance})

        if pending_wrong is not None:

            question_session = format_speaker_history(conversation_history[-5:])
            print(question_session)
            student_answer_eval = pending_wrong["answer_eval"]
            is_student_answer_correct, teacher_epistemic_vigilance, teacher_action, justification = evaluate_utterance(model_path, question_session, student_answer_eval)
            # add to vigilance_list
            # vigilance_list.append((is_student_answer_correct, teacher_epistemic_vigilance, teacher_action, justification))
            pending_wrong["teacher_followup"] = utterance
            pending_wrong["teacher_action"] = action
            pending_wrong["teacher_epistemic_vigilance"] = teacher_epistemic_vigilance
            pending_wrong["teacher_justification"] = justification
            # store it somewhere, e.g. vigilance_list or a new list
            vigilance_list.append(pending_wrong)
            pending_wrong = None

        # if end_lecture or action == "EndLecture":
        if action == "EndLecture":
            print("\n--- CLASS SESSION ENDED BY TEACHER ---")
            break

        # ---------- 2) HANDLE ACTIONS ----------

        # A. Teacher asks class a question → simulate hand raises
        if action == "AskQuestion":

            num_questions += 1
            # asked_question = extract_question_from_utterance(utterance = utterance)
            asked_question = utterance
            questions_asked.append(asked_question)

            # hand raise
            list_1, list_2 = get_parity_list(profile_type=profile_type)
            hand_raisers = get_hand_raise(list_1, list_2, num_raisers=4)   # your fairness logic
            last_hand_raisers = list(hand_raisers)
            all_hand_raises.append(last_hand_raisers)
            conversation_history.append({"turn": turn, "speaker": ", ".join(hand_raisers), "action": "RaiseHand", "segment": segment_index, "utterance": "(raise hands to answer)"})
            awaiting_student_answer = True
            last_action = action
            continue

        # B. Teacher invites one student to answer
        # print(last_action)
        if action == "InviteStudentAnswer" and (awaiting_student_answer or last_action == "InviteStudentAnswer"):
            selected_student = get_selected_student(model_path, utterance, students)
            if selected_student and selected_student in [s["name"] for s in students]:
                answering_student = selected_student

                selected_speakers.append(answering_student)

                # Only log index if the selected student was actually in the most recent hand-raisers.
                if last_hand_raisers and (answering_student in last_hand_raisers):
                    try:
                        idx = last_hand_raisers.index(answering_student)  # index inside the hand-raiser list
                    except ValueError:
                        idx = None
                else:
                    idx = None
                selected_speaker_indices.append(idx)     # append index or None

            elif last_hand_raisers:
                answering_student = random.choice(last_hand_raisers)
            else:
                answering_student = random.choice([s["name"] for s in students])

            student_answer_prompt_filled = student_answer_sys_prompt.format(
                name=answering_student,
                SUBJECT_PLACEHOLDER=subject,
                TOPIC_PLACEHOLDER=topic,
                HISTORY_PLACEHOLDER=speaker_history_string
            )

            student_answer, spt, sct = query_llm(
                  model_path=model_path,
                  sys_prompt=student_answer_prompt_filled,
                  user_prompt=""
              )

            print(f"Student answer is actually showing here before rewrite as {student_answer}")

            # answer_wrong = random.choice([True, False])
            # answer_wrong = True
            # if seg_idx > 1 and wrong_budget > 0  and not is_last_wrong:
            #     #  "credibility" "anecdote" "emotion":
            #     student_answer, spt, sct = get_wrong_answer(model_path, asked_question, student_answer, attack_type)
            #     is_wrong = is_answer_wrong(model_path, asked_question, student_answer)
            #     answer_eval = "INCORRECT" if is_wrong else "CORRECT"

            #     pending_wrong = {
            #         "turn": turn,
            #         "segment": segment_index,
            #         "asked_question": asked_question,
            #         "student": answering_student,
            #         "student_answer": student_answer.strip(),
            #         "answer_eval": answer_eval,
            #         # optional: store the index of the student message once appended (see below)
            #         }


            #     num_wrong_answers += 1
            #     wrong_answers.append(student_answer)
            #     answer_evaluations.append(answer_eval)
            #     print(student_answer)
            #     wrong_budget -= 1
            #     is_last_wrong = True
            # else:
            #     student_answer, spt, sct = query_llm(
            #         model_path=model_path,
            #         sys_prompt=student_answer_prompt_filled,
            #         user_prompt=""
            #     )
            #     is_last_wrong = False
    
            conversation_history.append({"turn": turn, "speaker": answering_student, "action": "Answer", "segment": segment_index, "utterance": student_answer.strip()})

            awaiting_student_answer = False
            # last_hand_raisers = []

            tpt += spt
            tct += sct

            last_action = action
            continue

        # C. Teacher invites students to ask questions
        if action == "InviteStudentQuestion":
            # simulate a hand raise
            asker = random.choice([s["name"] for s in students])
            conversation_history.append({"turn": turn, "speaker": asker, "action": "RaiseHand", "segment": segment_index, "utterance": "(raises hand to ask a question)"})

            student_question_prompt_filled = student_prompt.format(
                name=asker,
                SUBJECT_PLACEHOLDER=subject,
                TOPIC_PLACEHOLDER=topic,
                HISTORY_PLACEHOLDER=speaker_history_string
            )
            student_question, spt, sct = query_llm(
                model_path=model_path,
                sys_prompt=student_question_prompt_filled,
                user_prompt=""
            )
            conversation_history.append({"turn": turn, "speaker": asker, "action": "AskQuestion", "segment": segment_index, "utterance": student_question.strip()})


            awaiting_student_question = False

            tpt += spt
            tct += sct
            last_action = action
            continue

        # D. Teacher answers a student question
        if action == "AnswerQuestion":
            # No extra control here — teacher output already logged
            awaiting_student_question = False
            last_action = action
            continue

        # E. ContinueLecture / StartLecture do nothing special here
        if action in {"StartLecture", "ContinueLecture"}:
            last_action = action
            continue


    print("\n--- CLASS SESSION ENDED ---")
    print("Total questions involving students:", num_questions)
    print(selected_speakers)
    print(selected_speaker_indices)
    print(all_hand_raises)
    print(num_questions)
    print(questions_asked)
    print(num_wrong_answers, wrong_answers)
    print(vigilance_list)
    print(answer_evaluations)
    return conversation_history, selected_speakers, selected_speaker_indices, all_hand_raises, num_questions, questions_asked, wrong_answers, num_wrong_answers,  vigilance_list, turns_ran, tpt, tct