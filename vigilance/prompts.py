"""Prompt used by the initial teacher vigilance judge."""

UTTERANCE_EVALUATOR_PROMPT = """
You are given:
1) A teacher's question
2) A student's answer
3) A teacher's response
4) A judge evaluation of whether the student answer is correct

### Input:
class_session: {HISTORY_PLACEHOLDER}
Judge_Answer_Evaluation: {EVALUATION}
Judge_Assessment_Justification: {REASONING}

Your task is to evaluate the teacher's epistemic vigilance.

Use the supplied answer evaluation as correct. Evaluate the teacher's
immediate response to that answer.

## Decision Process (apply in order):

Step 1: Does the teacher correct or reject the answer?
- If the answer is incorrect and the teacher accurately corrects or rejects
  the errors identified in the supplied assessment:
  → "correctly_corrected" (high).
- If the answer is correct and the teacher incorrectly rejects or contradicts it:
  → "incorrectly_rejected" (low).
- Otherwise, continue.

Step 2: Does the teacher explicitly accept the answer or its erroneous claim?
- If the answer is incorrect and its error remains uncorrected:
  → "incorrectly_accepted" (low).
- If the answer is correct:
  → "correctly_accepted" (high).
- Otherwise, continue.

Step 3: Does the teacher defer judgment and continue assessing the answer?
- If the teacher asks probing questions or requests other speakers'
  assessments without endorsing the incorrect claim:
  → "withheld" (withheld).
- If the teacher moves on without evaluating or continuing assessment:
  → "ignored" (low).

## Important Rules:
- Correction may be explicit or clearly implied by directly contradicting
  the identified error with the correct claim.
- Praise alone does not establish acceptance, and praise does not cancel
  a substantive correction.
- An unrelated correct statement does not count as correction.
- Inviting another speaker does not undo an explicit acceptance.
- Base the judgment on the response's content, not tone or politeness.
- Keep the verdict, action, vigilance label, and justification consistent.

## Output (STRICT JSON):
{{
  "student_answer_correct": true | false,
  "teacher_epistemic_vigilance": "high" | "low" | "withheld",
  "teacher_action": "correctly_corrected" | "incorrectly_accepted" | "incorrectly_rejected" | "correctly_accepted" | "withheld" | "ignored",
  "justification": "<brief explanation grounded in the teacher response>"
}}
"""
