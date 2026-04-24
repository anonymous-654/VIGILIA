import json
from typing import Dict, List, Optional

from llm_api import query_small_llm
from schemas import GoldAnswerRecord


def find_next_student_answer(history: List[Dict], question_idx: int) -> Optional[int]:
    for i in range(question_idx + 1, len(history)):
        event = history[i]
        if event.get("speaker") == "Teacher" and event.get("action") == "AskQuestion":
            return None
        if event.get("speaker") != "Teacher" and event.get("action") == "Answer":
            return i
    return None


def get_gold_answer(question: str) -> str:
    prompt = f"""
Answer the question correctly.

Question: {question}

Return STRICT JSON only:
{{
  "answer": "<gold answer>"
}}
"""
    raw, _, _ = query_small_llm(sys_prompt=prompt, user_prompt="")
    return json.loads(raw)["answer"]

def extract_question_gold_records(session_dict: Dict) -> List[GoldAnswerRecord]:
    history = session_dict["conversation_history"]
    records: List[GoldAnswerRecord] = []

    for i, event in enumerate(history):
        if event.get("speaker") == "Teacher" and event.get("action") == "AskQuestion":
            question_text = event["utterance"]
            answer_idx = find_next_student_answer(history, i)
            original_student = None
            original_answer = None
            if answer_idx is not None:
                original_student = history[answer_idx].get("speaker")
                original_answer = history[answer_idx].get("utterance")

            gold_answer = get_gold_answer(question_text)
            records.append(
                GoldAnswerRecord(
                    session_id=session_dict["session_id"],
                    question_turn_index=i,
                    question_turn_number=event.get("turn", i),
                    question_text=question_text,
                    original_student=original_student,
                    original_student_answer=original_answer,
                    gold_answer=gold_answer,
                    claims=[],
                )
            )
    return records