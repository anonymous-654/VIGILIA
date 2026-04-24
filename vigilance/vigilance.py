import json
from typing import Dict, List

from classroom.class_utils import format_speaker_history
from corruption.gold import find_next_student_answer
from vigilance.teacher_followup import build_counterfactual_history, generate_teacher_followup
from llm_api import query_small_llm
from vigilance.prompts import UTTERANCE_EVALUATOR_PROMPT
from schemas import VigilanceEvalRecord


def evaluate_teacher_vigilance(history_string: str, answer_eval: str, answer_judge_justification: str) -> Dict:
    prompt = UTTERANCE_EVALUATOR_PROMPT.format(
        HISTORY_PLACEHOLDER=history_string,
        EVALUATION=answer_eval,
        REASONING=answer_judge_justification,
    )
    raw, _, _ = query_small_llm(sys_prompt=prompt, user_prompt="")
    return json.loads(raw)


def evaluate_single_styled_answer(session_dict: Dict, styled_record: Dict) -> VigilanceEvalRecord:
    history = session_dict["conversation_history"]
    q_idx = styled_record["question_turn_index"]
    q_event = history[q_idx]
    answer_idx = find_next_student_answer(history, q_idx)
    if answer_idx is None:
        raise ValueError("No student answer found after AskQuestion.")

    wrong_answer = styled_record["styled_wrong_answer"]
    answer_eval = styled_record["answer_eval"]
    answer_judge_justification = styled_record["incorrect_validator_reason"]
    counterfactual_history = build_counterfactual_history(history, answer_idx, wrong_answer)

    teacher_action, teacher_followup = generate_teacher_followup(
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
        history_string=format_speaker_history(eval_history),
        answer_eval = answer_eval,
        answer_judge_justification = answer_judge_justification,
        # answer_eval="INCORRECT",
    )

    return VigilanceEvalRecord(
        session_id=styled_record["session_id"],
        question_turn_index=styled_record["question_turn_index"],
        question_turn_number=styled_record["question_turn_number"],
        style_type=styled_record["style_type"],
        asked_question=q_event["utterance"],
        counterfactual_wrong_answer=wrong_answer,
        teacher_action_generated=teacher_action,
        teacher_followup=teacher_followup,
        answer_eval=answer_eval,
        answer_eval_justification=answer_judge_justification,
        teacher_epistemic_vigilance=eval_obj["teacher_epistemic_vigilance"],
        teacher_action_evaluated=eval_obj["teacher_action"],
        justification=eval_obj["justification"],
        metadata={},
    )