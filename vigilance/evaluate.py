# evaluate.py
import json
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm

from llm_utils import prompt_planner, prompt_speaker
from utils import format_full_history, format_speaker_history
from vigilance.utils import evaluate_utterance, get_wrong_answer, is_answer_wrong


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", type=str, required=True)
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--attack_type", type=str, default="credibility")
    parser.add_argument("--output_path", type=str, default=None)
    return parser.parse_args()


def load_sessions(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(path: str, results: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def default_output_path(input_path: str, attack_type:str, output_path: Optional[str]) -> str:
    if output_path:
        return output_path
    p = Path(input_path)
    return str(p.with_name(f"{p.stem}_counterfactual_vigilance_{attack_type}.json"))


def find_next_student_answer(
    history: List[Dict[str, Any]],
    question_idx: int,
) -> Optional[int]:
    """
    Find the first student Answer after a teacher AskQuestion.
    We stop early if another teacher AskQuestion starts before we find one.
    """
    for i in range(question_idx + 1, len(history)):
        event = history[i]
        speaker = event.get("speaker", "")
        action = event.get("action", "")

        if speaker == "Teacher" and action == "AskQuestion":
            return None

        if speaker != "Teacher" and action == "Answer":
            return i

    return None


def ensure_wrong_answer(
    model_path: str,
    asked_question: str,
    original_answer: str,
    attack_type: str,
    max_retries: int = 3,
) -> Tuple[str, str]:
    """
    Rewrite the original student answer into a wrong one.
    Returns: (wrong_answer, answer_eval)
    """
    rewritten = original_answer.strip()
    for _ in range(max_retries):
        rewritten, _, _ = get_wrong_answer(
            model_path=model_path,
            question=asked_question,
            correct_answer=rewritten,
            attack_type=attack_type,
        )
        rewritten = rewritten.strip()

        is_wrong, reasoning = is_answer_wrong(model_path, asked_question, rewritten)

        if is_wrong:
            return rewritten, "INCORRECT", reasoning

    final_eval = "INCORRECT" if is_wrong else "CORRECT"
    return rewritten, final_eval, reasoning


def build_counterfactual_history(
    history: List[Dict[str, Any]],
    answer_idx: int,
    wrong_answer: str,
) -> List[Dict[str, Any]]:
    """
    Copy the history up to and including the original answer turn, but replace
    the student answer utterance with the counterfactual wrong answer.
    """
    cf_history = [dict(x) for x in history[:answer_idx + 1]]
    cf_history[answer_idx]["utterance"] = wrong_answer
    return cf_history


def generate_teacher_followup(
    model_path: str,
    subject: str,
    topic: str,
    students: List[Dict[str, Any]],
    lesson_segments: List[str],
    counterfactual_history: List[Dict[str, Any]],
    segment_index: int,
) -> Tuple[str, str]:
    """
    Generate the teacher's next utterance from the modified history where the
    student's answer has been replaced with a wrong counterfactual.
    """

    history_string = format_full_history(counterfactual_history)
    speaker_history_string = format_speaker_history(counterfactual_history)

    # =========PLANNER DICISION ===========
    last_action = "InviteStudentAnswer"
    planner_json, pt, ct = prompt_planner(
                model_path=model_path,
                history_string=history_string,
                subject=subject,
                topic=topic,
                students=students,
                lesson_segments=lesson_segments,
                last_segment_index=segment_index,
                last_action=last_action,
                user_prompt=""
            )
   
    action = planner_json["next_action"]
    seg_idx = planner_json["next_segment_index"]
    reason = planner_json["reasoning"]

    # reason = (
    #     "A student has just answered the teacher's question. "
    #     "Respond naturally as the teacher to that answer."
    # )

    speaker_json, _, _ = prompt_speaker(
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



    teacher_action = action
    teacher_utterance = speaker_json["utterance"].strip()
    # print(teacher_action, teacher_utterance)
    return teacher_action, teacher_utterance


def evaluate_single_question(
    session: Dict[str, Any],
    question_idx: int,
    model_path: str,
    attack_type: str,
) -> Dict[str, Any]:
    history = session["conversation_history"]
    q_event = history[question_idx]

    asked_question = q_event["utterance"]
    segment_index = q_event.get("segment", 0)
    turn_number = q_event.get("turn", question_idx)

    answer_idx = find_next_student_answer(history, question_idx)
    if answer_idx is None:
        return {
            "question_turn_index": question_idx,
            "turn": turn_number,
            "segment": segment_index,
            "asked_question": asked_question,
            "error": "No student answer found after this AskQuestion."
        }

    answer_event = history[answer_idx]
    original_student = answer_event.get("speaker", "Student")
    original_answer = answer_event.get("utterance", "").strip()

    wrong_answer, answer_eval, reasoning = ensure_wrong_answer(
        model_path=model_path,
        asked_question=asked_question,
        original_answer=original_answer,
        attack_type=attack_type,
    )

    counterfactual_history = build_counterfactual_history(
        history=history,
        answer_idx=answer_idx,
        wrong_answer=wrong_answer,
    )

    subject = session.get("subject", "Unknown Subject")
    topic = session.get("topic", "Unknown Topic")
    students = session.get("students", [])
    lesson_segments = session.get("lesson_segments", [])

    teacher_action, teacher_followup = generate_teacher_followup(
        model_path=model_path,
        subject=subject,
        topic=topic,
        students=students,
        lesson_segments=lesson_segments,
        counterfactual_history=counterfactual_history,
        segment_index=segment_index,
    )

    eval_history = [dict(x) for x in counterfactual_history]
    eval_history.append({
        "turn": turn_number,
        "speaker": "Teacher",
        "action": teacher_action,
        "segment": segment_index,
        "utterance": teacher_followup,
    })

    question_session = format_speaker_history(eval_history)

    is_student_answer_correct, teacher_epistemic_vigilance, evaluated_teacher_action, justification = evaluate_utterance(
        model_path,
        question_session,
        answer_eval,
    )

    return {
        "question_turn_index": question_idx,
        "student_answer_turn_index": answer_idx,
        "turn": turn_number,
        "segment": segment_index,
        "asked_question": asked_question,
        "student": original_student,
        "original_student_answer": original_answer,
        "counterfactual_wrong_answer": wrong_answer,
        "reasoning_behind_answer_evaluation": reasoning,
        "answer_eval": answer_eval,
        "teacher_followup": teacher_followup,
        "teacher_action_generated": teacher_action,
        "teacher_action_evaluated": evaluated_teacher_action,
        "is_student_answer_correct": is_student_answer_correct,
        "teacher_epistemic_vigilance": teacher_epistemic_vigilance,
        "teacher_justification": justification,
    }


def run_vigilance_eval(
    sessions: List[Dict[str, Any]],
    model_path: str,
    attack_type: str,
) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []
    for session in tqdm(sessions, total=len(sessions), desc="Evaluating sessions"):
        history = session.get("conversation_history", [])
        question_results: List[Dict[str, Any]] = []

        for i, event in enumerate(history):
            if event.get("speaker") == "Teacher" and event.get("action") == "AskQuestion":
                try:
                    result = evaluate_single_question(
                        session=session,
                        question_idx=i,
                        model_path=model_path,
                        attack_type=attack_type,
                    )
                except Exception as e:
                    result = {
                        "question_turn_index": i,
                        "error": str(e),
                    }
                question_results.append(result)

                print(result)
                # break

        all_results.append({
            "profile_type": session.get("profile_type"),
            "session_index": session.get("session_index"),
            "subject": session.get("subject"),
            "topic": session.get("topic"),
            "num_questions_evaluated": len(question_results),
            "question_evaluations": question_results,
        })
        # break

    return all_results


def main():
    args = parse_args()

    sessions = load_sessions(args.input_path)
    results = run_vigilance_eval(
        sessions=sessions,
        model_path=args.model_path,
        attack_type=args.attack_type,
    )

    output_path = default_output_path(args.input_path, args.attack_type, args.output_path)
    save_results(output_path, results)
    print(f"Saved vigilance evaluation to: {output_path}")


    # ---- Compute overall epistemic vigilance score ----
    total_evaluations = 0
    high_vigilance_count = 0

    for session in results:
        for q in session.get("question_evaluations", []):
            if "teacher_epistemic_vigilance" in q:
                total_evaluations += 1
                if str(q["teacher_epistemic_vigilance"]).lower() == "high":
                    high_vigilance_count += 1

    if total_evaluations > 0:
        vigilance_score = high_vigilance_count / total_evaluations
    else:
        vigilance_score = 0

    print("\n===== Overall Epistemic Vigilance Score =====")
    print(f"High Vigilance: {high_vigilance_count}")
    print(f"Total Evaluations: {total_evaluations}")
    print(f"Score: {vigilance_score:.3f}")


if __name__ == "__main__":
    main()