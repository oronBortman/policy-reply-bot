import logging
import pytest
import json
from unittest.mock import Mock
from policy_bot.client import (
    parse_response,
    Answer,
    build_system_prompt,
    answer_question,
)
from test_utils import random_string

VALID_FILENAMES = {"hours.md", "products.md", "refunds.md"}

SAMPLE_KB = {
    "hours.md": "# Store hours\n\n- Monday-Friday: 9:00-18:00\n- Sunday: closed",
    "products.md": "# Products\n\n- Everyday Backpack - 20L, $65.\n- Trail Runner Jacket - $120.",
    "refunds.md": "# Refund policy\n\n- Refunds accepted within 30 days with a receipt.",
}


def make_mock_client(response_text, input_tokens=42, output_tokens=17):
    """Build a mock Anthropic-style client whose messages.create returns a
    canned response. `response_text` is the model's CONTINUATION text only
    (i.e. what response.content[0].text would hold after the "{" prefill —
    it must NOT itself start with "{")."""
    mock_response = Mock()
    mock_response.content = [Mock(text=response_text)]
    mock_response.usage = Mock(input_tokens=input_tokens, output_tokens=output_tokens)

    mock_client = Mock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


class TestClient:
    """Tests for policy_bot.client: response validation, prompt building,
    and the live API call."""

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

    def test_prompt_includes_every_kb_filename_and_content(self):
        """The built system prompt includes every KB file's name and content."""
        prompt = build_system_prompt(SAMPLE_KB)

        for filename, content in SAMPLE_KB.items():
            assert filename in prompt
            assert content in prompt

    def test_prompt_includes_item_not_found_instruction(self):
        """The built system prompt includes the topic-covered-but-item-not-found instruction."""
        prompt = build_system_prompt(SAMPLE_KB)

        # Must instruct the model to still use the topic's intent and citation,
        # and to say the specific item isn't carried, when the topic is covered
        # but the specific item is not listed (e.g. "do you sell shoes?").
        assert "isn't carried" in prompt or "is not carried" in prompt
        assert "still" in prompt.lower()
        assert "citation" in prompt.lower()

    def test_successful_mocked_call_returns_validated_answer(self):
        """A successful mocked API call returns a validated Answer."""
        response_text = json.dumps({
            "intent": "hours",
            "reply": "We are closed on Sundays.",
            "citations": ["hours.md"],
        })[1:]  # strip the leading "{" — that's the prefill, not the model's output
        client = make_mock_client(response_text)

        answer = answer_question("Are you open Sundays?", SAMPLE_KB, client)

        assert isinstance(answer, Answer)
        assert answer.intent == "hours"
        assert answer.reply == "We are closed on Sundays."
        assert answer.citations == ["hours.md"]

    def test_response_citing_unknown_file_raises_value_error(self):
        """A mocked API response citing a file outside the KB surfaces as a
        grounding failure, not a returned answer."""
        response_text = json.dumps({
            "intent": "hours",
            "reply": "We are closed on Sundays.",
            "citations": ["not_in_kb.md"],
        })[1:]
        client = make_mock_client(response_text)

        with pytest.raises(ValueError):
            answer_question("Are you open Sundays?", SAMPLE_KB, client)

    def test_call_made_with_temperature_zero_and_max_tokens_1024(self):
        """The API call is made with temperature=0 and max_tokens=1024."""
        response_text = json.dumps({
            "intent": "other",
            "reply": "I can't help with that.",
            "citations": [],
        })[1:]
        client = make_mock_client(response_text)

        answer_question("What's the weather?", SAMPLE_KB, client)

        _, kwargs = client.messages.create.call_args
        assert kwargs["extra_body"]["temperature"] == 0
        assert kwargs["max_tokens"] == 1024

    def test_call_conforms_to_real_messages_create_signature(self):
        """The call to client.messages.create() only uses keyword arguments
        the installed anthropic SDK's Messages.create() actually accepts. A
        plain Mock() (used by every other test here) accepts any kwarg
        silently, so it can't catch a real SDK/client.py mismatch — this
        test autospecs the real bound method so an unsupported kwarg raises
        TypeError here instead of at runtime against the live API."""
        import anthropic
        from unittest.mock import create_autospec

        response_text = json.dumps({
            "intent": "other",
            "reply": "I can't help with that.",
            "citations": [],
        })[1:]
        mock_response = Mock()
        mock_response.content = [Mock(text=response_text)]
        mock_response.usage = Mock(input_tokens=1, output_tokens=1)

        real_client = anthropic.Anthropic(api_key="test-key")
        client = Mock()
        client.messages.create = create_autospec(
            real_client.messages.create, return_value=mock_response
        )

        answer_question("What's the weather?", SAMPLE_KB, client)

    def test_messages_include_assistant_prefill_starting_with_brace(self):
        """The API call's message list includes an assistant-role prefill
        starting with "{"."""
        response_text = json.dumps({
            "intent": "other",
            "reply": "I can't help with that.",
            "citations": [],
        })[1:]
        client = make_mock_client(response_text)

        answer_question("What's the weather?", SAMPLE_KB, client)

        _, kwargs = client.messages.create.call_args
        messages = kwargs["messages"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        assert len(assistant_messages) == 1
        assert assistant_messages[0]["content"].startswith("{")

    def test_logs_latency_and_token_usage(self, caplog):
        """Latency and token counts are logged for every call."""
        response_text = json.dumps({
            "intent": "hours",
            "reply": "We are closed on Sundays.",
            "citations": ["hours.md"],
        })[1:]
        client = make_mock_client(response_text)

        with caplog.at_level(logging.INFO, logger="policy_bot.client"):
            answer_question("Are you open Sundays?", SAMPLE_KB, client)

        assert len(caplog.records) >= 1
