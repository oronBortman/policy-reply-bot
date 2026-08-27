import pytest
import json
from policy_bot.client import parse_response, Answer
from test_utils import random_string

VALID_FILENAMES = {"hours.md", "products.md", "refunds.md"}


class TestClient:
    """Tests for parse_response's grounding/validation rules."""

    @pytest.mark.parametrize("intent,citations", [
        ("hours", ["hours.md"]),
        ("other", []),
    ], ids=["topic-intent", "other-intent"])
    def test_well_formed_response_parses(self, intent, citations):
        """A well-formed response for a topic intent, and for an off-topic
        intent with no citations, both parse into a matching Answer."""
        reply_text = random_string()
        json_text = json.dumps({
            "intent": intent,
            "reply": reply_text,
            "citations": citations,
        })

        answer = parse_response(json_text, VALID_FILENAMES)

        assert isinstance(answer, Answer)
        assert answer.intent == intent
        assert answer.reply == reply_text
        assert answer.citations == citations

    @pytest.mark.parametrize("intent,citations", [
        ("hours", ["nonexistent.md"]),
        ("invalid_intent", ["hours.md"]),
        ("hours", []),
        ("refund", ["refunds.md", "hours.md"]),
    ], ids=["unknown-citation", "invalid-intent", "empty-citations", "too-many-citations"])
    def test_rejected_as_value_error(self, intent, citations):
        """A citation outside the KB, an invalid intent, or the wrong
        citation count for the intent are all rejected as ValueError."""
        json_text = json.dumps({
            "intent": intent,
            "reply": random_string(),
            "citations": citations,
        })

        with pytest.raises(ValueError):
            parse_response(json_text, VALID_FILENAMES)

    def test_malformed_json_rejected_as_value_error(self):
        """Text that isn't valid JSON at all is rejected as ValueError."""
        with pytest.raises(ValueError):
            parse_response("{ invalid json }", VALID_FILENAMES)

    @pytest.mark.parametrize("missing_field", ["intent", "reply", "citations"])
    def test_missing_field_rejected_as_value_error(self, missing_field):
        """JSON missing any one required field is rejected as ValueError."""
        data = {"intent": "hours", "reply": random_string(), "citations": ["hours.md"]}
        del data[missing_field]
        json_text = json.dumps(data)

        with pytest.raises(ValueError):
            parse_response(json_text, VALID_FILENAMES)

    def test_direct_construction_has_no_grounding_logic(self):
        """Answer is a pure data model — constructing it directly (e.g. a
        test fixture representing an expected value) never runs the
        grounding check. Grounding is parse_response's job, not Answer's."""
        answer = Answer(intent="hours", reply=random_string(), citations=["not-a-real-file.md"])

        assert answer.intent == "hours"
        assert answer.citations == ["not-a-real-file.md"]
