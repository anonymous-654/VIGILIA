"""LLM routes: selected teacher model and configurable Azure helpers.

GEMMA_BASE_URL and QWEN_BASE_URL override the normal local endpoints.
AZURE_OPENAI_DEPLOYMENT selects the GPT deployment used by the small helpers.
"""

import os
import time
import logging
from functools import lru_cache
from types import SimpleNamespace
from openai.types import CompletionUsage

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

from core.json_utils import parse_fenced_json_response
from core.llm_text import extract_response_from_local_llm

load_dotenv()

logger = logging.getLogger(__name__)
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
HELPER_DEPLOYMENT = os.getenv("AZURE_HELPER_DEPLOYMENT", deployment)


def _local_client(env_name, default_url):
    return OpenAI(
        base_url=os.getenv(env_name, default_url),
        api_key="EMPTY",
        timeout=float(os.getenv("LOCAL_LLM_TIMEOUT_SECONDS", "300")),
        max_retries=0,
    )


gemma_client = _local_client("GEMMA_BASE_URL", "http://localhost:8000/v1")
gemma_12b_client = _local_client("GEMMA_12B_BASE_URL", "http://localhost:8000/v1")
gemma_nt_client = _local_client("GEMMA_NT_BASE_URL", "http://localhost:8000/v1")
qwen_client = _local_client("QWEN_BASE_URL", "http://localhost:8000/v1")
qwen_38_client = _local_client("QWEN_38_BASE_URL", "http://localhost:8000/v1")


@lru_cache(maxsize=1)
def _get_gpt_client():
    # Local-only workflows do not require Azure credentials.
    return AzureOpenAI(
        azure_endpoint=os.getenv("AZUREOPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION", "2024-12-01-preview"),
    )


@lru_cache(maxsize=1)
def _get_claude_client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is required for Claude teacher models")
    from anthropic import Anthropic

    return Anthropic(api_key=key)


@lru_cache(maxsize=1)
def _get_gemini_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is required for Gemini teacher models")
    from google import genai

    return genai.Client(api_key=key)


def _native_completion(provider, client, model, sys_prompt, user_prompt, temperature):
    # Existing callers often put the entire task in the system prompt.
    user = (
        user_prompt
        if user_prompt and user_prompt.strip()
        else "Respond to the system instructions."
    )
    if provider == "claude":
        kwargs = dict(
            model=model,
            messages=[{"role": "user", "content": user}],
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "8192")),
        )
        if sys_prompt:
            kwargs["system"] = sys_prompt
        response = client.messages.create(**kwargs)
        result = "".join(
            block.text for block in response.content if block.type == "text"
        )
        usage = response.usage
        pt = (
            usage.input_tokens
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        )
        ct = usage.output_tokens
        if response.stop_reason == "max_tokens":
            raise ValueError("Claude response truncated; increase CLAUDE_MAX_TOKENS")
    else:
        config = {"temperature": temperature}
        if sys_prompt:
            config["system_instruction"] = sys_prompt
        response = client.models.generate_content(
            model=model, contents=user, config=config
        )
        result = response.text
        usage = response.usage_metadata
        pt = getattr(usage, "prompt_token_count", 0) or 0
        ct = (getattr(usage, "candidates_token_count", 0) or 0) + (
            getattr(usage, "thoughts_token_count", 0) or 0
        )
        if any(
            str(c.finish_reason).endswith("MAX_TOKENS")
            for c in (response.candidates or [])
        ):
            raise ValueError("Gemini response truncated")
    if not result:
        raise ValueError(
            f"{provider} returned no text (blocked, refused, or empty response)"
        )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=result))],
        usage=CompletionUsage(
            prompt_tokens=pt, completion_tokens=ct, total_tokens=pt + ct
        ),
    )


def _luna_completion(client, model, sys_prompt, user_prompt):
    """Collect Azure Responses streaming output into the shared completion shape."""
    messages = []
    if sys_prompt is not None:
        messages.append({"role": "system", "content": sys_prompt})
    if user_prompt is not None:
        messages.append({"role": "user", "content": user_prompt})
    chunks = []
    completed = None
    with client.responses.create(
        model=model,
        service_tier="default",
        input=messages,
        temperature=1,
        text={"format": {"type": "text"}, "verbosity": "medium"},
        reasoning={"effort": "medium", "mode": "standard", "summary": "auto"},
        tools=[],
        stream=True,
        store=True,
        include=["reasoning.encrypted_content", "web_search_call.action.sources"],
    ) as stream:
        for event in stream:
            if event.type in ("response.output_text.delta", "response.refusal.delta"):
                chunks.append(event.delta)
            elif event.type == "error":
                raise RuntimeError(event.message)
            elif event.type in ("response.failed", "response.incomplete"):
                detail = getattr(event.response, "error", None) or getattr(
                    event.response, "incomplete_details", None
                )
                raise RuntimeError(f"Azure Responses {event.type}: {detail}")
            elif event.type == "response.completed":
                completed = event.response
    if completed is None:
        raise ValueError("Azure Responses stream ended without response.completed")
    result = "".join(chunks)
    if not result:
        raise ValueError("Azure Responses returned no text")
    usage = completed.usage
    if usage is None:
        raise ValueError("Azure Responses returned no token usage")
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=result))],
        usage=CompletionUsage(
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
        ),
    )


def _create_chat_completion_with_retries(
    client, max_attempts=5, retry_sleep_seconds=5, request_fn=None, **kwargs
):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            response = (
                request_fn()
                if request_fn is not None
                else client.chat.completions.create(**kwargs)
            )
            return response
        except Exception as exc:
            elapsed = time.time() - t0
            last_error = exc
            print(
                f"[WARN] LLM request failed attempt={attempt}/{max_attempts} "
                f"after {elapsed:.1f}s: {type(exc).__name__}: {exc}",
                flush=True,
            )
            if attempt == max_attempts:
                break
            time.sleep(retry_sleep_seconds * attempt)

    raise last_error


def _query_chat(
    client,
    model,
    sys_prompt,
    user_prompt,
    temperature,
    max_attempts,
    extra_body=None,
    azure=False,
):
    messages = []
    if sys_prompt is not None:
        messages.append({"role": "system", "content": sys_prompt})
    if user_prompt is not None:
        messages.append({"role": "user", "content": user_prompt})
    kwargs = dict(model=model, messages=messages)
    if azure:
        # Azure model is the exact deployment name, not an inferred model ID.
        # GPT-5 deployments may reject seed and non-default sampling settings.
        if "gpt-5" not in model.lower():
            kwargs["temperature"] = temperature
    elif client is qwen_client or client is qwen_38_client:
        # Qwen sampling follows the requested thinking mode, including JSON calls.
        qwen_body = dict(extra_body or {})
        qwen_body.update(top_k=20, min_p=0.0, repetition_penalty=1.0)
        thinking = qwen_body.get("chat_template_kwargs", {}).get(
            "enable_thinking", True
        )
        kwargs.update(
            seed=42,
            temperature=1.0 if thinking else 0.7,
            top_p=0.95 if thinking else 0.80,
            presence_penalty=1.5,
            extra_body=qwen_body,
        )
    elif (
        client is gemma_client
        or client is gemma_12b_client
        or client is gemma_nt_client
    ):
        gemma_body = dict(extra_body or {})
        gemma_body.update(top_k=64)
        kwargs.update(seed=42, temperature=1.0, top_p=0.95, extra_body=gemma_body)
    else:
        kwargs.update(seed=42, temperature=temperature, extra_body=extra_body)
    if (
        client is qwen_client
        or client is qwen_38_client
        or client is gemma_client
        or client is gemma_12b_client
        or client is gemma_nt_client
    ):
        max_attempts = min(
            max_attempts, max(1, int(os.getenv("LOCAL_LLM_MAX_ATTEMPTS", "2")))
        )
    response = _create_chat_completion_with_retries(
        client, max_attempts=max_attempts, **kwargs
    )

    msg = response.choices[0].message
    result = msg.content
    if result is None:
        result = getattr(msg, "reasoning_content", None)
    if result is None:
        raise ValueError(
            f"LLM returned neither content nor reasoning_content. Full message: {msg}"
        )
    return (
        extract_response_from_local_llm(result),
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )


def query_llm(
    model_path: str,
    sys_prompt: str = None,
    user_prompt: str = "",
    temperature=0,
    max_attempts=5,
):
    """Teacher routes: Claude, Gemini, Azure deployment, or local Qwen/Gemma.

    Local Qwen/Gemma names ending in -nt disable thinking; the suffix is not sent to the server.
    GPT-6 Luna uses streaming Azure Responses with medium/standard reasoning.
    Native IDs or anthropic/claude-..., google/gemini-... are accepted.
    Use azure/DEPLOYMENT for arbitrary Azure deployment names. GPT-5 routes
    omit temperature and seed to preserve the deployment's supported defaults.
    """
    name = model_path.lower()
    model = model_path.split("/", 1)[-1]
    if name.startswith(
        ("claude-", "anthropic/claude-", "gemini-", "google/gemini-", "models/gemini-")
    ):
        provider = "claude" if "claude-" in name else "gemini"
        client = _get_claude_client() if provider == "claude" else _get_gemini_client()
        response = _create_chat_completion_with_retries(
            client,
            max_attempts=max_attempts,
            model=model,
            request_fn=lambda: _native_completion(
                provider, client, model, sys_prompt, user_prompt, temperature
            ),
        )
        return (
            response.choices[0].message.content,
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
    if name.startswith("azure/") or "gpt" in name:
        if model.lower() == "gpt-6-luna":
            client = _get_gpt_client()
            response = _create_chat_completion_with_retries(
                client,
                max_attempts=max_attempts,
                model=model,
                request_fn=lambda: _luna_completion(
                    client, model, sys_prompt, user_prompt
                ),
            )
            return (
                extract_response_from_local_llm(response.choices[0].message.content),
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
        return _query_chat(
            _get_gpt_client(),
            model_path[6:] if name.startswith("azure/") else model_path,
            sys_prompt,
            user_prompt,
            temperature,
            max_attempts,
            azure=True,
        )
    # Only local Qwen/Gemma routes interpret -nt; callers retain their experiment ID.
    thinking = not name.endswith("-nt")
    request_model = model_path if thinking else model_path[:-3]
    model = request_model.split("/", 1)[-1]
    if model.lower() == "qwen3.8-27b":
        client = qwen_38_client
    elif "qwen" in name:
        client = qwen_client
    elif "gemma" in name and not thinking:
        client = gemma_nt_client
    elif model.lower() == "gemma-4-12b-it-tt":
        client = gemma_12b_client
    elif "gemma" in name:
        client = gemma_client
    else:
        raise ValueError(
            f"Unknown teacher model: {model_path}. Use Claude, Gemini, GPT, azure/DEPLOYMENT, Qwen, or Gemma."
        )
    return _query_chat(
        client,
        request_model,
        sys_prompt,
        user_prompt,
        temperature,
        max_attempts,
        {"chat_template_kwargs": {"enable_thinking": thinking}},
    )


def query_corruption_llm(
    sys_prompt: str = None, user_prompt: str = "", temperature=0, max_attempts=5
):
    """Use the configured Azure helper for gold answers, corruptions and rewrites."""
    return _query_chat(
        _get_gpt_client(),
        HELPER_DEPLOYMENT,
        sys_prompt,
        user_prompt,
        temperature,
        max_attempts,
    )


def query_small_llm(
    sys_prompt: str = None, user_prompt: str = "", temperature=0, max_attempts=5
):
    """Use the Azure GPT deployment for student responses and auxiliary tasks."""

    return _query_chat(
        _get_gpt_client(),
        HELPER_DEPLOYMENT,
        sys_prompt,
        user_prompt,
        temperature,
        max_attempts,
    )


def _query_json_with_retries(
    query_fn, max_attempts=5, raw_preview_chars=1000, **kwargs
):
    last_raw = None
    last_error = None
    last_prompt_tokens = 0
    last_completion_tokens = 0

    for attempt in range(1, max_attempts + 1):
        raw, prompt_tokens, completion_tokens = query_fn(**kwargs)
        last_raw = raw
        last_prompt_tokens = prompt_tokens
        last_completion_tokens = completion_tokens

        try:
            return parse_fenced_json_response(raw), prompt_tokens, completion_tokens
        except Exception as exc:
            last_error = exc
            preview = "" if raw is None else raw[:raw_preview_chars]
            print(
                f"[WARN] JSON parse failed attempt={attempt}/{max_attempts}: "
                f"{type(exc).__name__}: {exc}"
            )
            logger.debug("Raw response preview: %r", preview)

    print(f"[ERROR] JSON parse failed after {max_attempts} attempts.")
    logger.debug("Last raw response: %r", last_raw)
    raise ValueError(
        f"LLM did not return valid JSON after {max_attempts} attempts. "
        f"Last token usage: prompt={last_prompt_tokens}, completion={last_completion_tokens}. "
        f"Last error: {last_error}"
    ) from last_error


def query_json_llm(
    model_path: str,
    sys_prompt: str = None,
    user_prompt: str = "",
    temperature=0,
    max_attempts=5,
):
    return _query_json_with_retries(
        query_llm,
        max_attempts=max_attempts,
        model_path=model_path,
        sys_prompt=sys_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )


def query_small_json_llm(
    sys_prompt: str = None,
    user_prompt: str = "",
    temperature=0,
    max_attempts=5,
):
    return _query_json_with_retries(
        query_small_llm,
        max_attempts=max_attempts,
        sys_prompt=sys_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )


def query_corruption_json_llm(
    sys_prompt: str = None,
    user_prompt: str = "",
    temperature=0,
    max_attempts=5,
):
    """JSON counterpart of query_corruption_llm, with JSON parse retries."""
    return _query_json_with_retries(
        query_corruption_llm,
        max_attempts=max_attempts,
        sys_prompt=sys_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
    )
