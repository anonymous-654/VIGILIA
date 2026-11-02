import unittest
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, Mock, patch
from llm import client


class TeacherProviderTests(unittest.TestCase):
    def test_claude_system_only_json(self):
        fake = Mock()
        fake.messages.create.return_value = NS(
            content=[NS(type="text", text='{"ok":true}')],
            stop_reason="end_turn",
            usage=NS(
                input_tokens=10,
                output_tokens=3,
                cache_read_input_tokens=2,
                cache_creation_input_tokens=1,
            ),
        )
        with patch.object(client, "_get_claude_client", return_value=fake):
            self.assertEqual(
                client.query_json_llm("claude-haiku-4-5", sys_prompt="task"),
                ({"ok": True}, 13, 3),
            )
        kw = fake.messages.create.call_args.kwargs
        self.assertEqual(kw["system"], "task")
        self.assertTrue(kw["messages"][0]["content"])
        self.assertNotIn("extra_body", kw)
        self.assertNotIn("temperature", kw)

    def test_gemini_usage_and_prefix(self):
        fake = Mock()
        fake.models.generate_content.return_value = NS(
            text="answer",
            usage_metadata=NS(
                prompt_token_count=10, candidates_token_count=4, thoughts_token_count=5
            ),
            candidates=[],
        )
        with patch.object(client, "_get_gemini_client", return_value=fake):
            self.assertEqual(
                client.query_llm("google/gemini-2.5-flash", sys_prompt="task"),
                ("answer", 10, 9),
            )
        kw = fake.models.generate_content.call_args.kwargs
        self.assertEqual(kw["model"], "gemini-2.5-flash")
        self.assertEqual(kw["config"]["system_instruction"], "task")

    def test_azure_deployment_and_gpt5_parameters(self):
        fake = Mock()
        fake.chat.completions.create.return_value = NS(
            choices=[NS(message=NS(content="answer"))],
            usage=NS(prompt_tokens=2, completion_tokens=3),
        )
        with patch.object(client, "_get_gpt_client", return_value=fake):
            client.query_llm("azure/gpt-5.4_mini")
        kw = fake.chat.completions.create.call_args.kwargs
        self.assertEqual(kw["model"], "gpt-5.4_mini")
        for key in ["seed", "temperature", "extra_body"]:
            self.assertNotIn(key, kw)

    def luna_stream(self, events):
        stream = MagicMock()
        stream.__enter__.return_value = iter(events)
        return stream

    def test_luna_responses_routing_and_json(self):
        for name in ("gpt-6-luna", "azure/gpt-6-luna"):
            with self.subTest(model=name):
                fake = Mock()
                fake.responses.create.return_value = self.luna_stream(
                    [
                        NS(type="response.output_text.delta", delta='{"ok":'),
                        NS(type="response.output_text.delta", delta="true}"),
                        NS(
                            type="response.completed",
                            response=NS(
                                usage=NS(
                                    input_tokens=12, output_tokens=8, total_tokens=20
                                )
                            ),
                        ),
                    ]
                )
                with patch.object(client, "_get_gpt_client", return_value=fake):
                    self.assertEqual(
                        client.query_json_llm(
                            name, sys_prompt="task", user_prompt="question"
                        ),
                        ({"ok": True}, 12, 8),
                    )
                kw = fake.responses.create.call_args.kwargs
                self.assertEqual(kw["model"], "gpt-6-luna")
                self.assertEqual(
                    kw["input"],
                    [
                        {"role": "system", "content": "task"},
                        {"role": "user", "content": "question"},
                    ],
                )
                self.assertEqual(
                    kw["reasoning"],
                    {"effort": "medium", "mode": "standard", "summary": "auto"},
                )
                self.assertEqual(
                    kw["text"], {"format": {"type": "text"}, "verbosity": "medium"}
                )
                self.assertEqual(kw["temperature"], 1)
                self.assertEqual(kw["service_tier"], "default")
                self.assertEqual(kw["tools"], [])
                self.assertTrue(kw["store"])
                self.assertTrue(kw["stream"])
                self.assertEqual(
                    kw["include"],
                    ["reasoning.encrypted_content", "web_search_call.action.sources"],
                )
                fake.chat.completions.create.assert_not_called()

    def test_luna_stream_errors_retry_and_close(self):
        for terminal in (
            NS(type="error", message="failure"),
            NS(type="response.failed", response=NS(error="failure")),
            NS(type="response.incomplete", response=NS(incomplete_details="limit")),
            None,
        ):
            with self.subTest(event=terminal):
                fake = Mock()
                events = [NS(type="response.output_text.delta", delta="partial")]
                if terminal is not None:
                    events.append(terminal)
                streams = [self.luna_stream(events), self.luna_stream(events)]
                fake.responses.create.side_effect = streams
                with (
                    patch.object(client, "_get_gpt_client", return_value=fake),
                    patch.object(client.time, "sleep"),
                ):
                    with self.assertRaises((RuntimeError, ValueError)):
                        client.query_llm("gpt-6-luna", max_attempts=2)
                self.assertEqual(fake.responses.create.call_count, 2)
                for stream in streams:
                    stream.__exit__.assert_called_once()

    def test_qwen_thinking_sampling_for_text_and_json(self):
        for model in ("Qwen/Qwen3.5-27B", "Qwen/Qwen3.5-27B-FP8"):
            for query in (client.query_llm, client.query_json_llm):
                with self.subTest(model=model, query=query.__name__):
                    fake = Mock()
                    fake.chat.completions.create.return_value = NS(
                        choices=[NS(message=NS(content='{"ok":true}'))],
                        usage=NS(prompt_tokens=2, completion_tokens=3),
                    )
                    with patch.object(client, "qwen_client", fake):
                        query(model, temperature=0)
                    kw = fake.chat.completions.create.call_args.kwargs
                    self.assertEqual(kw["model"], model)
                    self.assertEqual(kw["temperature"], 1.0)
                    self.assertEqual(kw["top_p"], 0.95)
                    self.assertEqual(kw["presence_penalty"], 1.5)
                    self.assertEqual(kw["seed"], 42)
                    self.assertEqual(
                        kw["extra_body"],
                        {
                            "chat_template_kwargs": {"enable_thinking": True},
                            "top_k": 20,
                            "min_p": 0.0,
                            "repetition_penalty": 1.0,
                        },
                    )

    def test_gemma_sampling_for_text_and_json(self):
        for query in (client.query_llm, client.query_json_llm):
            with self.subTest(query=query.__name__):
                fake = Mock()
                fake.chat.completions.create.return_value = NS(
                    choices=[NS(message=NS(content='{"ok":true}'))],
                    usage=NS(prompt_tokens=2, completion_tokens=3),
                )
                with patch.object(client, "gemma_client", fake):
                    query("google/gemma-4-31B-it", temperature=0)
                kw = fake.chat.completions.create.call_args.kwargs
                self.assertEqual(kw["model"], "google/gemma-4-31B-it")
                self.assertEqual(kw["temperature"], 1.0)
                self.assertEqual(kw["top_p"], 0.95)
                self.assertEqual(kw["seed"], 42)
                self.assertEqual(
                    kw["extra_body"],
                    {"chat_template_kwargs": {"enable_thinking": True}, "top_k": 64},
                )
                self.assertNotIn("presence_penalty", kw)

    def test_gemma_12b_teacher_route(self):
        for query in (client.query_llm, client.query_json_llm):
            fake = Mock()
            fake.chat.completions.create.return_value = NS(
                choices=[NS(message=NS(content='{"ok":true}'))],
                usage=NS(prompt_tokens=2, completion_tokens=3),
            )
            with (
                patch.object(client, "gemma_12b_client", fake),
                patch.object(client, "gemma_client") as other,
            ):
                query("google/gemma-4-12B-it-tt")
                other.chat.completions.create.assert_not_called()
            kw = fake.chat.completions.create.call_args.kwargs
            self.assertEqual(kw["model"], "google/gemma-4-12B-it-tt")
            self.assertEqual(kw["temperature"], 1.0)
            self.assertEqual(kw["top_p"], 0.95)
            self.assertEqual(
                kw["extra_body"],
                {"chat_template_kwargs": {"enable_thinking": True}, "top_k": 64},
            )

    def test_qwen_38_teacher_route(self):
        for query in (client.query_llm, client.query_json_llm):
            fake = Mock()
            fake.chat.completions.create.return_value = NS(
                choices=[NS(message=NS(content='{"ok":true}'))],
                usage=NS(prompt_tokens=2, completion_tokens=3),
            )
            with (
                patch.object(client, "qwen_38_client", fake),
                patch.object(client, "qwen_client") as old,
            ):
                query("Qwen/Qwen3.8-27B")
                old.chat.completions.create.assert_not_called()
            kw = fake.chat.completions.create.call_args.kwargs
            self.assertEqual(kw["model"], "Qwen/Qwen3.8-27B")
            self.assertEqual(kw["temperature"], 1.0)
            self.assertEqual(kw["top_p"], 0.95)
            self.assertEqual(kw["presence_penalty"], 1.5)
            self.assertEqual(kw["seed"], 42)
            self.assertEqual(
                kw["extra_body"],
                {
                    "chat_template_kwargs": {"enable_thinking": True},
                    "top_k": 20,
                    "min_p": 0.0,
                    "repetition_penalty": 1.0,
                },
            )

    def test_non_thinking_aliases(self):
        cases = [
            ("Qwen/Qwen3.5-27B", "qwen_client"),
            ("Qwen/Qwen3.5-27B-FP8", "qwen_client"),
            ("Qwen/Qwen3.8-27B", "qwen_38_client"),
            ("google/gemma-4-12B-it-tt", "gemma_nt_client"),
            ("google/gemma-4-31B-it", "gemma_nt_client"),
        ]
        for model, route in cases:
            for query in (client.query_llm, client.query_json_llm):
                with self.subTest(model=model, query=query.__name__):
                    fake = Mock()
                    fake.chat.completions.create.return_value = NS(
                        choices=[NS(message=NS(content='{"ok":true}'))],
                        usage=NS(prompt_tokens=2, completion_tokens=3),
                    )
                    alias = model + "-nt"
                    with patch.object(client, route, fake):
                        query(alias)
                    kw = fake.chat.completions.create.call_args.kwargs
                    self.assertEqual(kw["model"], model)
                    self.assertEqual(alias, model + "-nt")
                    self.assertEqual(kw["seed"], 42)
                    body = kw["extra_body"]
                    self.assertFalse(body["chat_template_kwargs"]["enable_thinking"])
                    qwen = model.startswith("Qwen/")
                    self.assertEqual(kw["temperature"], 0.7 if qwen else 1.0)
                    self.assertEqual(kw["top_p"], 0.80 if qwen else 0.95)
                    self.assertEqual(body["top_k"], 20 if qwen else 64)
                    if qwen:
                        self.assertEqual(kw["presence_penalty"], 1.5)
                        self.assertEqual(body["min_p"], 0.0)
                        self.assertEqual(body["repetition_penalty"], 1.0)
                    else:
                        self.assertNotIn("presence_penalty", kw)
                        self.assertNotIn("min_p", body)
                        self.assertNotIn("repetition_penalty", body)

    def test_local_route_unchanged(self):
        with patch.object(client, "_query_chat", return_value=("answer", 1, 2)) as call:
            client.query_llm("google/gemma-4-31B-it")
            self.assertIs(call.call_args.args[0], client.gemma_client)
            self.assertTrue(
                call.call_args.args[-1]["chat_template_kwargs"]["enable_thinking"]
            )

    def test_empty_response_retried(self):
        fake = Mock()
        fake.models.generate_content.return_value = NS(
            text=None, usage_metadata=None, candidates=[]
        )
        with (
            patch.object(client, "_get_gemini_client", return_value=fake),
            patch.object(client.time, "sleep"),
        ):
            with self.assertRaises(ValueError):
                client.query_llm("gemini-2.5-flash", max_attempts=2)
        self.assertEqual(fake.models.generate_content.call_count, 2)


if __name__ == "__main__":
    unittest.main()
