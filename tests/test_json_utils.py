import json
import unittest

from core.json_utils import parse_fenced_json_response


class ParseFencedJsonResponseTests(unittest.TestCase):
    def test_repairs_actual_escaped_value_delimiters(self):
        raw = r"""{"feature_evidence": [{"feature": "A-prefixing", "evidence_span": \"the data is a-providin' evidence\", "explanation": "Uses a-prefixing."}], "updated_text": "the data is a-providin' evidence"}"""

        parsed = parse_fenced_json_response(raw)

        self.assertEqual(
            parsed["feature_evidence"][0]["evidence_span"],
            "the data is a-providin' evidence",
        )

    def test_repairs_mixed_extra_closing_quote(self):
        raw = r"""{"evidence_span": \"someone is a-intervenin'\"", "updated_text": "someone is a-intervenin'"}"""

        parsed = parse_fenced_json_response(raw)

        self.assertEqual(parsed["evidence_span"], "someone is a-intervenin'")

    def test_repairs_trailing_comma(self):
        parsed = parse_fenced_json_response('{"applicable": true,}')
        self.assertEqual(parsed, {"applicable": True})

    def test_preserves_valid_escaped_quotes_and_backslashes(self):
        raw = r'{"text": "She said \"hello\".", "path": "C:\\tmp"}'
        self.assertEqual(parse_fenced_json_response(raw), json.loads(raw))

    def test_still_repairs_bare_backslashes(self):
        parsed = parse_fenced_json_response('{"formula": "\\alpha + \\beta"}')
        self.assertEqual(parsed["formula"], "\\alpha + \\beta")


if __name__ == "__main__":
    unittest.main()
