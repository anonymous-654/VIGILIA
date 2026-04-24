from enums import AttackType
from llm_api import query_llm, query_small_llm
from utils import parse_json_string
from vigilance.prompts import ANECDOTAL_WRONG_REWRITE_PROMPT, ANSWER_EVALUATOR, CREDIBILITY_WRONG_REWRITE_PROMPT, EMOTIONAL_WRONG_REWRITE_PROMPT, PLAIN_WRONG_REWRITE_PROMPT, UTTERANCE_EVALUATOR, WRONG_ANSWER_EXTRACTION_PROMPT


def get_wrong_answer(model_path:str, question: str, correct_answer:str, attack_type: str):

    if attack_type == AttackType.CREDIBILITY:
      prompt = CREDIBILITY_WRONG_REWRITE_PROMPT
    elif attack_type == AttackType.ANECDOTE:
      prompt = ANECDOTAL_WRONG_REWRITE_PROMPT
    elif attack_type == AttackType.EMOTION:
      prompt = EMOTIONAL_WRONG_REWRITE_PROMPT
    elif attack_type == AttackType.PLAIN:
      prompt = PLAIN_WRONG_REWRITE_PROMPT
    else:
      pass
    prompt = prompt.format(
        QUESTION=question,
        CORRECT_ANSWER=correct_answer
    )
    raw, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=prompt,
        user_prompt="",
        temperature=0.7
    )

    # raw, pt, ct = query_small_llm(
    #     sys_prompt=prompt,
    #     user_prompt=""
    # )
    output = parse_json_string(raw)
    return output["wrong_answer"], pt, ct

def get_correct_answer(question:str):
    prompt =  f"""
    Given a question. Answer the question correctly

    QUESTION: {question}

    Output (STRICT JSON only):
    {{
      "answer": "<correct answer>"
    }}"""

    raw, pt, ct = query_small_llm(
        sys_prompt=prompt,
        user_prompt=""
    )
    output = parse_json_string(raw)
    return output["answer"], pt, ct

def is_answer_wrong(model_path, question: str, answer: str):
    prompt = ANSWER_EVALUATOR.format(
        QUESTION=question,
        ANSWER=answer
    )
    raw, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=prompt,)
    output = parse_json_string(raw)
    return output["verdict"] == "INCORRECT", output["reasoning"]


def evaluate_utterance(model_path, history_string, evaluation: str):
    prompt = UTTERANCE_EVALUATOR.format(
        HISTORY_PLACEHOLDER=history_string, EVALUATION=evaluation)
    raw, pt, ct = query_llm(
        model_path=model_path,
        sys_prompt=prompt,)
    output = parse_json_string(raw)

    # print(output)
    is_student_answer_correct = output["student_answer_correct"]
    teacher_epistemic_vigilance = output["teacher_epistemic_vigilance"]
    teacher_action = output["teacher_action"]
    justification = output["justification"]
    return is_student_answer_correct, teacher_epistemic_vigilance, teacher_action, justification
