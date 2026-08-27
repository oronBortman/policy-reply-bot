import json
import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path
import anthropic

from policy_bot.cli import main
from policy_bot.client import Answer


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


class TestCLINetworkError:
    """Test: Running the CLI when answer_question raises anthropic.APIError prints error to stderr and exits non-zero."""

    def test_cli_network_error_prints_error_to_stderr_and_exits_nonzero(self, capsys):
        """CLI when answer_question raises anthropic.APIError prints error to stderr and exits with non-zero code."""
        error_msg = "Connection timeout"
        # Create a mock request for the APIConnectionError
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


class TestCLIValueError:
    """Test: Running the CLI when answer_question raises ValueError prints error to stderr and exits non-zero."""

    def test_cli_value_error_prints_error_to_stderr_and_exits_nonzero(self, capsys):
        """CLI when answer_question raises ValueError prints error to stderr and exits with non-zero code."""
        error_msg = "Malformed JSON: missing required field"

        with patch("policy_bot.cli.answer_question", side_effect=ValueError(error_msg)):
            with patch("policy_bot.cli.load_kb", return_value={"hours.md": "content"}):
                with pytest.raises(SystemExit) as exc_info:
                    sys.argv = ["cli", "Are you open?"]
                    main()

                assert exc_info.value.code != 0

        captured = capsys.readouterr()
        assert error_msg in captured.err
