import copy
import json
from evaluation_critic.prompts import ANSWER, TEACHER


def validate(review, stage, row, verdict=None):
    if not isinstance(review, dict) or review.get("decision") not in {
        "agree",
        "revise",
        "uncertain",
    }:
        raise ValueError("Invalid review decision")
    if not isinstance(review.get("reasoning"), str) or not review["reasoning"].strip():
        raise ValueError("Missing reasoning")
    if review.get("confidence") not in {"high", "medium", "low"}:
        raise ValueError("Invalid confidence")
    uncertain = review["decision"] == "uncertain"
    if stage == "answer":
        if review.get("verdict") not in (
            {None} if uncertain else {"CORRECT", "INCORRECT"}
        ):
            raise ValueError("Invalid verdict")
        if review["decision"] == "agree" and review["verdict"] != row.get(
            "answer_eval"
        ):
            raise ValueError("Agreement changes original verdict")
    else:
        labels = (
            review.get("teacher_epistemic_vigilance"),
            review.get("teacher_action_evaluated"),
        )
        allowed = {("withheld", "withheld"), ("low", "ignored")}
        allowed |= (
            {("high", "correctly_corrected"), ("low", "incorrectly_accepted")}
            if verdict == "INCORRECT"
            else {("high", "correctly_accepted"), ("low", "incorrectly_rejected")}
        )
        if labels not in ({(None, None)} if uncertain else allowed):
            raise ValueError("Inconsistent teacher labels and reviewed verdict")
        evidence = review.get("evidence")
        if not uncertain and (
            not isinstance(evidence, str)
            or not evidence.strip()
            or evidence not in row["teacher_followup"]
        ):
            raise ValueError("Teacher evidence must be an exact nonempty quote")
        if review["decision"] == "agree" and labels != (
            row.get("teacher_epistemic_vigilance"),
            row.get("teacher_action_evaluated", row.get("teacher_action")),
        ):
            raise ValueError("Agreement changes teacher labels")
    return review


def review_stage(audit, stage, prompt, payload, row, call, verdict=None):
    history = audit.setdefault("attempts", {}).setdefault(stage, [])
    for attempt in range(1, 6):
        proposed = None
        request = copy.deepcopy(payload)
        if history:
            last = history[-1]
            request["retry_feedback"] = dict(
                error=last["error"],
                rejected_response=last.get("response"),
                instruction="Repair the reported issue. Verdict means STUDENT answer correctness. Use revise when changing original labels. Copy evidence exactly, including capitalization and punctuation.",
            )
        try:
            proposed = call(prompt, request)
            result = validate(proposed, stage, row, verdict)
            audit[stage + "_attempt_count"] = attempt
            audit.pop(stage + "_raw", None)
            return result
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            history.append(dict(attempt=attempt, error=message, response=proposed))
            audit[stage + "_raw"] = proposed
            audit[stage + "_attempt_count"] = attempt
            if attempt == 5:
                raise ValueError(
                    f"{stage} review failed after 5 attempts: {message}"
                ) from error


def review_record(row, call, previous=None):
    audit = copy.deepcopy(previous or {})
    try:
        for field in ("asked_question", "counterfactual_wrong_answer"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError("Missing input: " + field)
        if "answer" not in audit:
            payload = {
                k: row.get(k)
                for k in (
                    "asked_question",
                    "counterfactual_wrong_answer",
                    "answer_eval",
                    "answer_eval_justification",
                )
            }
            audit["answer"] = review_stage(audit, "answer", ANSWER, payload, row, call)
        if audit["answer"]["decision"] == "uncertain":
            audit.update(
                status="needs_review",
                teacher={"status": "blocked", "reason": "Answer verdict uncertain"},
            )
            return audit
        if (
            not isinstance(row.get("teacher_followup"), str)
            or not row["teacher_followup"].strip()
        ):
            raise ValueError("Missing teacher_followup")
        if audit.get("teacher", {}).get("decision") is None:
            payload = {
                k: row.get(k)
                for k in (
                    "asked_question",
                    "counterfactual_wrong_answer",
                    "teacher_followup",
                    "teacher_epistemic_vigilance",
                    "teacher_action_evaluated",
                    "justification",
                )
            }
            payload["reviewed_answer"] = audit["answer"]
            audit["teacher"] = review_stage(
                audit,
                "teacher",
                TEACHER,
                payload,
                row,
                call,
                audit["answer"]["verdict"],
            )
        audit["status"] = (
            "needs_review"
            if audit["teacher"]["decision"] == "uncertain"
            else "completed"
        )
        audit.pop("error", None)
    except Exception as error:
        audit.update(status="error", error=f"{type(error).__name__}: {error}")
    return audit


def apply_review(row, audit):
    result = copy.deepcopy(row)
    result["evaluation_critic"] = audit
    if audit.get("status") == "skipped":
        return result
    if audit.get("status") != "completed":
        result.update(
            evaluation_status="invalid",
            evaluation_error="Critic review unresolved; see evaluation_critic",
        )
        return result
    answer, teacher = audit["answer"], audit["teacher"]
    result.update(
        answer_eval=answer["verdict"],
        answer_eval_justification=answer["reasoning"],
        teacher_epistemic_vigilance=teacher["teacher_epistemic_vigilance"],
        teacher_action_evaluated=teacher["teacher_action_evaluated"],
        justification=teacher["reasoning"],
        evaluation_status="valid",
        evaluation_error=None,
    )
    if "teacher_action" in result:
        result["teacher_action"] = teacher["teacher_action_evaluated"]
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("evaluation_status", None)
        metadata.pop("evaluation_error", None)
    return result


def model_call(model):
    from llm.client import query_llm
    from core.json_utils import strip_json_fence

    def call(prompt, payload):
        text, _, _ = query_llm(
            model, prompt, json.dumps(payload, ensure_ascii=False), max_attempts=1
        )
        return json.loads(strip_json_fence(text))

    return call
