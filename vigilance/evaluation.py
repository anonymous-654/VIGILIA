import time
from vigilance.validity import invalid_reason
from typing import Dict, List

from core.history import format_dialogue_only
from corruption.gold import find_next_student_answer
from vigilance.teacher_followup import (
    build_counterfactual_history,
    generate_teacher_followup,
)
from llm.client import query_small_json_llm
from vigilance.prompts import UTTERANCE_EVALUATOR_PROMPT
from schemas import LanguagePhenomenonVigilanceEvalRecord, VigilanceEvalRecord


REQUIRED_VIGILANCE_KEYS = (
    "teacher_epistemic_vigilance",
    "teacher_action",
    "justification",
)


def _missing_keys(obj: Dict, required_keys) -> List[str]:
    return [key for key in required_keys if key not in obj]


def evaluate_teacher_vigilance(
    history_string: str,
    answer_eval: str,
    answer_judge_justification: str,
    max_attempts: int = 5,
) -> Dict:
    prompt = UTTERANCE_EVALUATOR_PROMPT.format(
        HISTORY_PLACEHOLDER=history_string,
        EVALUATION=answer_eval,
        REASONING=answer_judge_justification,
    )
    last_error = None
    last_response = None

    for attempt in range(1, max_attempts + 1):
        try:
            eval_obj, _, _ = query_small_json_llm(sys_prompt=prompt, user_prompt="")
            last_response = eval_obj
            if not isinstance(eval_obj, dict):
                raise ValueError("Evaluator response must be an object")
            missing = _missing_keys(eval_obj, REQUIRED_VIGILANCE_KEYS)
            if missing:
                raise KeyError(
                    f"Vigilance evaluator response missing keys {missing}: {eval_obj}"
                )
            reason = invalid_reason(eval_obj)
            if reason:
                raise ValueError(reason)
            return dict(eval_obj, evaluation_status="valid")
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            print(
                f"[WARN] Vigilance evaluator failed attempt={attempt}/{max_attempts}: "
                f"{type(exc).__name__}: {exc}"
            )
            time.sleep(2 * attempt)

    raw = last_response if isinstance(last_response, dict) else {}
    return {
        "teacher_epistemic_vigilance": str(
            raw.get("teacher_epistemic_vigilance", "invalid")
        ),
        "teacher_action": str(raw.get("teacher_action", "invalid")),
        "justification": str(raw.get("justification", "Evaluation unavailable")),
        "evaluation_status": "invalid",
        "evaluation_error": str(last_error),
        "raw_evaluator_response": last_response,
    }


def evaluate_single_styled_answer(
    session_dict: Dict, styled_record: Dict
) -> VigilanceEvalRecord:
    history = session_dict["conversation_history"]
    q_idx = styled_record["question_turn_index"]
    q_event = history[q_idx]
    answer_idx = find_next_student_answer(history, q_idx)
    if answer_idx is None:
        raise ValueError("No student answer found after AskQuestion.")

    answering_student = history[answer_idx].get("speaker")
    wrong_answer = styled_record["styled_wrong_answer"]
    answer_eval = styled_record["answer_eval"]
    answer_judge_justification = styled_record["incorrect_validator_reason"]
    counterfactual_history = build_counterfactual_history(
        history, answer_idx, wrong_answer
    )

    teacher_action, teacher_followup = generate_teacher_followup(
        log_context=f"session={session_dict.get('session_id')} question_index={q_idx}",
        model_path=session_dict["metadata"]["model_path"],
        subject=session_dict["subject"],
        topic=session_dict["topic"],
        students=session_dict["students"],
        lesson_segments=session_dict["lesson_segments"],
        counterfactual_history=counterfactual_history,
        segment_index=q_event.get("segment", 0),
    )

    eval_history = [dict(x) for x in counterfactual_history]
    eval_history.append(
        {
            "turn": q_event.get("turn", q_idx),
            "speaker": "Teacher",
            "action": teacher_action,
            "segment": q_event.get("segment", 0),
            "utterance": teacher_followup,
        }
    )

    eval_obj = evaluate_teacher_vigilance(
        history_string=format_dialogue_only(eval_history),
        answer_eval=answer_eval,
        answer_judge_justification=answer_judge_justification,
    )

    return VigilanceEvalRecord(
        session_id=styled_record["session_id"],
        subject=session_dict.get("subject", ""),
        topic=session_dict.get("topic", ""),
        question_turn_index=styled_record["question_turn_index"],
        question_turn_number=styled_record["question_turn_number"],
        style_type=styled_record["style_type"],
        asked_question=q_event["utterance"],
        answering_student=answering_student,
        counterfactual_wrong_answer=wrong_answer,
        teacher_action_generated=teacher_action,
        teacher_followup=teacher_followup,
        answer_eval=answer_eval,
        answer_eval_justification=answer_judge_justification,
        teacher_epistemic_vigilance=eval_obj["teacher_epistemic_vigilance"],
        teacher_action_evaluated=eval_obj["teacher_action"],
        justification=eval_obj["justification"],
        evaluation_status=eval_obj.get("evaluation_status", "valid"),
        evaluation_error=eval_obj.get("evaluation_error"),
        raw_evaluator_response=eval_obj.get("raw_evaluator_response"),
        metadata={
            "record_type": "styled_corruption",
        },
    )


def evaluate_single_language_phenomenon_answer(
    session_dict: Dict,
    phenomenon_record: Dict,
) -> LanguagePhenomenonVigilanceEvalRecord:
    history = session_dict["conversation_history"]
    q_idx = phenomenon_record["question_turn_index"]
    q_event = history[q_idx]
    answer_idx = find_next_student_answer(history, q_idx)
    if answer_idx is None:
        raise ValueError("No student answer found after AskQuestion.")

    answering_student = history[answer_idx].get("speaker")
    wrong_answer = phenomenon_record["updated_wrong_answer"]
    answer_eval = phenomenon_record["answer_eval"]
    answer_judge_justification = phenomenon_record["incorrect_validator_reason"]
    counterfactual_history = build_counterfactual_history(
        history, answer_idx, wrong_answer
    )

    teacher_action, teacher_followup = generate_teacher_followup(
        log_context=f"session={session_dict.get('session_id')} question_index={q_idx}",
        model_path=session_dict["metadata"]["model_path"],
        subject=session_dict["subject"],
        topic=session_dict["topic"],
        students=session_dict["students"],
        lesson_segments=session_dict["lesson_segments"],
        counterfactual_history=counterfactual_history,
        segment_index=q_event.get("segment", 0),
    )

    eval_history = [dict(x) for x in counterfactual_history]
    eval_history.append(
        {
            "turn": q_event.get("turn", q_idx),
            "speaker": "Teacher",
            "action": teacher_action,
            "segment": q_event.get("segment", 0),
            "utterance": teacher_followup,
        }
    )

    eval_obj = evaluate_teacher_vigilance(
        history_string=format_dialogue_only(eval_history),
        answer_eval=answer_eval,
        answer_judge_justification=answer_judge_justification,
    )

    return LanguagePhenomenonVigilanceEvalRecord(
        session_id=phenomenon_record["session_id"],
        subject=session_dict.get("subject", ""),
        topic=session_dict.get("topic", ""),
        question_turn_index=phenomenon_record["question_turn_index"],
        question_turn_number=phenomenon_record["question_turn_number"],
        phenomenon_type=phenomenon_record["phenomenon_type"],
        selected_item=phenomenon_record["selected_item"],
        selected_items=phenomenon_record.get("selected_items", []),
        num_instances=phenomenon_record.get("num_instances", 0),
        selection_reason=phenomenon_record["selection_reason"],
        asked_question=q_event["utterance"],
        answering_student=answering_student,
        counterfactual_wrong_answer=wrong_answer,
        teacher_action_generated=teacher_action,
        teacher_followup=teacher_followup,
        answer_eval=answer_eval,
        answer_eval_justification=answer_judge_justification,
        teacher_epistemic_vigilance=eval_obj["teacher_epistemic_vigilance"],
        teacher_action_evaluated=eval_obj["teacher_action"],
        justification=eval_obj["justification"],
        evaluation_status=eval_obj.get("evaluation_status", "valid"),
        evaluation_error=eval_obj.get("evaluation_error"),
        raw_evaluator_response=eval_obj.get("raw_evaluator_response"),
        metadata={
            "record_type": phenomenon_record.get("record_type"),
            "num_added_words": phenomenon_record.get("num_added_words"),
            "applicable": phenomenon_record.get("applicable"),
            "applicability_reason": phenomenon_record.get("applicability_reason"),
            "phenomenon_definition": phenomenon_record.get("phenomenon_definition"),
            "yale_url": phenomenon_record.get("yale_url"),
            "dialect_type": phenomenon_record.get("dialect_type"),
            "applied_features": phenomenon_record.get("applied_features"),
            "feature_evidence": phenomenon_record.get("feature_evidence"),
        },
    )
