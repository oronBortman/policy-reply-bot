import json
import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path
import anthropic

from policy_bot.cli import main
from policy_bot.client import Answer
from test_utils import random_string


@pytest.fixture(autouse=True)
def anthropic_api_key(monkeypatch):
    """Give every CLI test a fake API key by default so behavior doesn't
    depend on the ambient environment. TestCLIMissingAPIKey overrides this
    within itself via monkeypatch.delenv."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


class TestCLISuccess:
    """Test: Running the CLI with a message prints JSON and exits 0."""

    def test_cli_success_prints_json_to_stdout_and_exits_0(self, capsys):
        """CLI with a valid message prints JSON answer to stdout and exits 0."""
        expected_answer = Answer(
            intent="hours",
            reply="We are open 9-5 on weekdays.",
            citations=["hours.md"]
        )

        with patch("policy_bot.cli.answer_question", return_value=expected_answer):
            with patch("policy_bot.cli.load_kb", return_value={"hours.md": "content"}):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["intent"] == "hours"
        assert output["reply"] == "We are open 9-5 on weekdays."
        assert output["citations"] == ["hours.md"]


class TestCLIErrorHandling:
    """Test: running the CLI when answer_question raises any of the caught
    exception types prints the error message to stderr and exits non-zero,
    instead of a raw traceback."""

    @pytest.mark.parametrize("exception_type", [
        ValueError,
        IndexError,
        AttributeError,
    ])
    def test_error_prints_to_stderr_and_exits_nonzero(self, capsys, exception_type):
        """Each caught exception type prints its message to stderr and exits non-zero."""
        error_msg = random_string()

        with patch("policy_bot.cli.answer_question", side_effect=exception_type(error_msg)):
            with patch("policy_bot.cli.load_kb", return_value={"hours.md": "content"}):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert error_msg in captured.err


class TestCLINetworkError:
    """Test: Running the CLI when answer_question raises anthropic.APIError prints error to stderr and exits non-zero."""

    def test_cli_network_error_prints_error_to_stderr_and_exits_nonzero(self, capsys):
        """CLI when answer_question raises anthropic.APIError prints error to stderr and exits with non-zero code."""
        error_msg = random_string()
        mock_request = Mock()
        api_error = anthropic.APIConnectionError(message=error_msg, request=mock_request)

        with patch("policy_bot.cli.answer_question", side_effect=api_error):
            with patch("policy_bot.cli.load_kb", return_value={"hours.md": "content"}):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert error_msg in captured.err


class TestCLINonAsciiOutput:
    """Test: non-ASCII characters in a reply (e.g. an en dash) print
    literally in the CLI's JSON output, not as \\uXXXX escapes."""

    def test_cli_prints_non_ascii_characters_literally_not_escaped(self, capsys):
        """A reply containing an en dash prints as a literal character in
        stdout, not as a \\uXXXX escape sequence."""
        expected_answer = Answer(
            intent="hours",
            reply="We are open Monday–Friday.",
            citations=["hours.md"]
        )

        with patch("policy_bot.cli.answer_question", return_value=expected_answer):
            with patch("policy_bot.cli.load_kb", return_value={"hours.md": "content"}):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "Monday–Friday" in captured.out
        assert "\\u2013" not in captured.out


class TestCLIMissingAPIKey:
    """Test: running the CLI with no ANTHROPIC_API_KEY set prints a clear
    error to stderr and exits non-zero, without attempting any KB load or
    API call."""

    def test_cli_missing_api_key_prints_clear_error_and_exits_nonzero(self, capsys, monkeypatch):
        """No ANTHROPIC_API_KEY set prints a clear error and exits non-zero,
        without ever calling load_kb or answer_question."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        mock_answer_question = Mock()
        mock_load_kb = Mock()

        with patch("policy_bot.cli.answer_question", mock_answer_question):
            with patch("policy_bot.cli.load_kb", mock_load_kb):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.err
        mock_load_kb.assert_not_called()
        mock_answer_question.assert_not_called()


