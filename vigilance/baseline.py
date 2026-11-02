"""Canonical unstyled evaluations, cached once per session/question/context."""

import copy
import hashlib
import json
import os
from pathlib import Path
import fcntl
from tqdm import tqdm
from vigilance.validity import invalid_reason
from functools import lru_cache

from core.json_io import load_json
from config import evaluation_model_dir


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def records(path):
    obj = load_json(Path(path))
    return obj if isinstance(obj, list) else [obj]


def key(row):
    return str(row["session_id"]) + ":" + str(row["question_turn_index"])


def _read_settings():
    root = Path(__file__).resolve().parents[1]
    files = [
        "llm/client.py",
        "llm/classroom.py",
        "llm/classroom_prompts.py",
        "vigilance/evaluation.py",
        "vigilance/prompts.py",
        "vigilance/teacher_followup.py",
        "vigilance/baseline.py",
        "core/history.py",
    ]
    return {
        "code": {f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in files},
        "env": {
            k: os.getenv(k)
            for k in [
                "AZURE_OPENAI_DEPLOYMENT",
                "AZURE_HELPER_DEPLOYMENT",
                "AZUREOPENAI_ENDPOINT",
                "AZURE_API_VERSION",
                "GEMMA_BASE_URL",
                "GEMMA_12B_BASE_URL",
                "GEMMA_NT_BASE_URL",
                "QWEN_BASE_URL",
                "QWEN_38_BASE_URL",
            ]
        },
    }


@lru_cache(maxsize=1)
def _settings_snapshot():
    current = _read_settings()
    expected = os.getenv("VIGILANCE_SETTINGS_SNAPSHOT")
    if expected and current != json.loads(expected):
        raise ValueError(
            "Pipeline code/config changed since launch; refusing to start a new "
            "evaluation stage with different settings. Completed outputs are preserved."
        )
    return current


def settings():
    # Snapshot once per process; disk edits must not relabel imported runtime code.
    return copy.deepcopy(_settings_snapshot())


def cache_path(session_path):
    sessions = records(session_path)
    model = sessions[0]["metadata"]["model_path"]
    return evaluation_model_dir("baseline", model) / (
        Path(session_path).stem + "_baseline_cache.json"
    )


def atomic_save(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    temporary.replace(path)


def canonical_inputs(session_path, canonical_path):
    sessions = {s["session_id"]: s for s in records(session_path)}
    result = {}
    config = settings()
    for group in records(canonical_path):
        for base in group.get("base_corruptions", []):
            if base["session_id"] not in sessions:
                continue
            k = key(base)
            if k in result:
                raise ValueError("Duplicate canonical baseline: " + k)
            session = sessions[base["session_id"]]
            canonical = {
                f: base[f]
                for f in [
                    "session_id",
                    "question_turn_index",
                    "question_turn_number",
                    "question_text",
                    "base_wrong_answer",
                    "validator_verdict",
                    "validator_reasoning",
                ]
            }
            result[k] = (session, canonical, digest([session, canonical, config]))
    return result


def reusable_entry(entry, session, base, fingerprint):
    if not entry:
        return False
    if entry.get("fingerprint") == fingerprint:
        return True
    return os.getenv("VIGILANCE_REUSE_CACHED_BASELINES") == "1" and entry.get(
        "input_digest"
    ) == digest([session, base])


def load_baselines(session_path, canonical_path, create=False):
    """Readers never regenerate: main evaluation is the baseline-producing stage."""
    expected = canonical_inputs(session_path, canonical_path)
    path = cache_path(session_path)
    # Serialize writers, including separate pipeline invocations, and checkpoint each success.
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = load_json(path) if path.exists() else {}
        output = {}
        reused = sum(
            k in saved
            and not saved[k].get("retryable_error")
            and reusable_entry(saved[k], v[0], v[1], v[2])
            for k, v in expected.items()
        )
        print(
            f"[BASELINE] total={len(expected)} reused={reused} pending={len(expected)-reused}",
            flush=True,
        )
        for k, (session, base, fingerprint) in tqdm(
            expected.items(),
            total=len(expected),
            desc="Shared baselines",
            unit="question",
            mininterval=5,
        ):
            entry = saved.get(k)
            if not reusable_entry(entry, session, base, fingerprint) or (
                create and entry.get("retryable_error")
            ):
                if not create:
                    raise ValueError(
                        "Missing/stale shared baseline; run main evaluation first: " + k
                    )
                from vigilance.evaluation import evaluate_single_styled_answer

                styled = dict(
                    base,
                    style_type="plain",
                    styled_wrong_answer=base["base_wrong_answer"],
                    answer_eval=base["validator_verdict"],
                    incorrect_validator_reason=base["validator_reasoning"],
                )
                failure = None
                try:
                    result = evaluate_single_styled_answer(session, styled).model_dump()
                except Exception as exc:
                    failure = f"{type(exc).__name__}: {exc}"
                    print(
                        f"[BASELINE FAILED] session/question={k} {failure}; continuing",
                        flush=True,
                    )
                    result = {
                        "session_id": base["session_id"],
                        "question_turn_index": base["question_turn_index"],
                        "question_turn_number": base["question_turn_number"],
                        "subject": session.get("subject", ""),
                        "topic": session.get("topic", ""),
                        "style_type": "plain",
                        "asked_question": base["question_text"],
                        "answering_student": None,
                        "counterfactual_wrong_answer": base["base_wrong_answer"],
                        "teacher_action_generated": None,
                        "teacher_followup": None,
                        "answer_eval": base["validator_verdict"],
                        "answer_eval_justification": base["validator_reasoning"],
                        "teacher_epistemic_vigilance": "invalid",
                        "teacher_action_evaluated": "invalid",
                        "justification": "Baseline evaluation failed; excluded from metrics.",
                        "evaluation_status": "invalid",
                        "evaluation_error": failure,
                        "metadata": {"record_type": "styled_corruption"},
                    }
                result.setdefault("metadata", {})["baseline_fingerprint"] = fingerprint
                entry = {
                    "fingerprint": fingerprint,
                    "result": result,
                    "settings": settings(),
                    "input_digest": digest([session, base]),
                    "retryable_error": failure or invalid_reason(result),
                }
                saved[k] = entry
                atomic_save(path, saved)
            output[k] = copy.deepcopy(entry["result"])
            if entry.get("fingerprint") != fingerprint:
                output[k].setdefault("metadata", {})[
                    "historical_baseline_reused"
                ] = True
                output[k]["metadata"][
                    "historical_baseline_note"
                ] = "Explicit reuse with matching inputs; original settings retained in cache."
        failures = {
            k: saved[k]["result"].get("evaluation_error") or saved[k]["retryable_error"]
            for k in output
            if saved[k].get("retryable_error")
        }
        atomic_save(path.with_suffix(".failures.json"), failures)
        print(
            f"[BASELINE SUMMARY] total={len(output)} failed={len(failures)}; "
            "failed entries will retry on the next main evaluation",
            flush=True,
        )
        return output


def baseline_for(base, shared, phenomenon=False):
    k = key(base)
    if k not in shared:
        raise ValueError("Family has no canonical baseline: " + k)
    result = copy.deepcopy(shared[k])
    if result["counterfactual_wrong_answer"] != base["base_wrong_answer"]:
        raise ValueError("Family unstyled answer conflicts with canonical answer: " + k)
    if phenomenon:
        result.pop("style_type", None)
        result.update(
            phenomenon_type="baseline",
            selected_item="",
            selected_items=[],
            num_instances=0,
            selection_reason="Shared canonical unstyled evaluation.",
        )
    return result


def output_signature(session_path, grouped_path, canonical_path):
    shared = load_baselines(session_path, canonical_path)
    return digest(
        [
            records(session_path),
            records(grouped_path),
            shared,
            settings(),
            "shared-baseline-v1",
        ]
    )


def stamp_output(path, session_path, grouped_path, canonical_path):
    atomic_save(
        Path(str(path) + ".inputs.json"),
        {
            "signature": output_signature(session_path, grouped_path, canonical_path),
            "settings": settings(),
        },
    )


def output_is_current(path, session_path, grouped_path, canonical_path):
    try:
        sidecar = load_json(Path(str(path) + ".inputs.json"))
        return sidecar["signature"] == output_signature(
            session_path, grouped_path, canonical_path
        )
    except (OSError, ValueError, KeyError):
        return False
