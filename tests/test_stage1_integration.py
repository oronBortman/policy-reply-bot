"""Full-pipeline integration tests (Task 5).

These tests wire the REAL load_kb, build_system_prompt, answer_question, and
cli.main() together against the REAL knowledge base files on disk. The one
and only mock boundary is the Anthropic SDK client class itself
(policy_bot.cli.anthropic.Anthropic) — its .messages.create(...) return
value is canned so no live network call is ever made.

Do NOT patch policy_bot.cli.load_kb or policy_bot.cli.answer_question here —
that's what Task 4's own tests (tests/test_cli.py) do, mocking at the module
boundary. This test proves the pieces actually integrate.
"""
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from policy_bot.cli import main

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"


@pytest.fixture(autouse=True)
def anthropic_api_key(monkeypatch):
    """cli.main() now checks ANTHROPIC_API_KEY upfront; give these
    integration tests a fake one so they don't depend on the ambient
    environment (the Anthropic client class itself is mocked anyway)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def make_mock_response(intent, reply, citations, input_tokens=42, output_tokens=17):
    """Build a canned Anthropic-SDK-shaped response.

    response.content[0].text holds the model's JSON with the leading "{"
    stripped, since answer_question() prepends the "{" assistant-prefill
    itself before parsing.
    """
    response_text = json.dumps({"intent": intent, "reply": reply, "citations": citations})[1:]
    mock_response = Mock()
    mock_response.content = [Mock(text=response_text)]
    mock_response.usage = Mock(input_tokens=input_tokens, output_tokens=output_tokens)
    return mock_response


def make_mock_anthropic_class(response):
    """Build a mock replacement for the anthropic.Anthropic class: calling
    it (as cli.py does via `anthropic.Anthropic()`) returns a mock client
    whose .messages.create(...) returns the canned response."""
    mock_client = Mock()
    mock_client.messages.create.return_value = response
    mock_anthropic_class = Mock(return_value=mock_client)
    return mock_anthropic_class


class TestStage1QuestionsFullPipeline:
    """Test: each stage-1 question, run through the real CLI/client/kb wiring
    with only the Anthropic client mocked, prints the correct JSON and exits 0."""

    @pytest.mark.parametrize(
        "question, intent, reply, citations",
        [
            (
                "Are you open on Sundays?",
                "hours",
                "No, we're closed on Sundays.",
                ["hours.md"],
            ),
            (
                "I bought a jacket 10 days ago, can I get my money back?",
                "refund",
                "Yes, refunds are accepted within 30 days of purchase with a receipt.",
                ["refunds.md"],
            ),
            (
                "What backpacks do you sell?",
                "product",
                "We carry the Everyday Backpack, 20L, $65, in black or olive.",
                ["products.md"],
            ),
            (
                "Can you help me file my taxes?",
                "other",
                "Sorry, I can't help with that.",
                [],
            ),
        ],
        ids=["hours", "refund", "product", "other"],
    )
    def test_stage1_question_prints_correct_json_and_exits_0(
        self, capsys, question, intent, reply, citations
    ):
        """Each stage-1 use case, run through the real wiring with only the
        Anthropic client mocked, prints the expected intent/reply/citations
        as JSON and exits 0."""
        mock_response = make_mock_response(intent, reply, citations)
        mock_anthropic_class = make_mock_anthropic_class(mock_response)

        with patch("policy_bot.cli.anthropic.Anthropic", mock_anthropic_class):
            with pytest.raises(SystemExit) as exc_info:
                sys.argv = ["cli", question]
                main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["intent"] == intent
        assert output["reply"] == reply
        assert output["citations"] == citations


class TestStage1PromptContainsRealKBContent:
    """Test: the prompt actually sent to the mocked client contains real
    content from all 3 KB files on disk, proving cli.py -> client.py -> kb.py
    are genuinely wired together, not mocked in isolation."""

    def test_prompt_sent_to_mock_contains_all_kb_file_contents(self, capsys):
        """The system prompt actually sent to the mocked client contains
        every real KB file's name and content from disk."""
        mock_response = make_mock_response("hours", "We're closed Sundays.", ["hours.md"])
        mock_anthropic_class = make_mock_anthropic_class(mock_response)

        with patch("policy_bot.cli.anthropic.Anthropic", mock_anthropic_class):
            with pytest.raises(SystemExit) as exc_info:
                sys.argv = ["cli", "Are you open on Sundays?"]
                main()

            assert exc_info.value.code == 0

        mock_client = mock_anthropic_class.return_value
        _, kwargs = mock_client.messages.create.call_args
        system_prompt = kwargs["system"]

        for kb_file in sorted(KB_DIR.glob("*.md")):
            assert kb_file.name in system_prompt
            assert kb_file.read_text() in system_prompt
