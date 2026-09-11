"""Stage 1 golden-set e2e test (Task 6).

Unlike Tasks 1-5, this makes REAL calls to the Anthropic API against the
REAL knowledge base on disk. No mocks anywhere in this file. It is marked
`@pytest.mark.e2e` and excluded from the default `pytest` run (see
pytest.ini) since it costs real API calls and real money per run. Run it
deliberately with:

    pytest -m e2e -s

The `-s` flag is required to see the printed replies (they're not asserted
on, since wording is non-deterministic across runs -- a human reads them
next to `expected_answer` to judge facts/tone).

`intent` and `citations` ARE asserted -- they should be deterministic given
temperature=0 and a fixed knowledge base.
"""
import json
from pathlib import Path

import anthropic
import pytest

from policy_bot.client import answer_question
from policy_bot.kb import load_kb

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"
SAMPLE_QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_questions.json"


def _load_stage1_questions():
    with open(SAMPLE_QUESTIONS_PATH) as f:
        all_questions = json.load(f)
    return [q for q in all_questions if q["stage"] == 1]


STAGE1_QUESTIONS = _load_stage1_questions()


@pytest.mark.e2e
class TestStage1GoldenSet:
    """Test: each stage-1 question, run against the real Anthropic API and
    the real knowledge base, produces the expected intent and citations."""

    @pytest.mark.parametrize(
        "case",
        STAGE1_QUESTIONS,
        ids=[q["id"] for q in STAGE1_QUESTIONS],
    )
    def test_stage1_question_matches_expected_intent_and_citations(self, case):
        """Real API call, real KB: intent and citations match the golden
        expectation; reply is printed (not asserted) for manual review."""
        client = anthropic.Anthropic()
        kb = load_kb(KB_DIR)

        answer = answer_question(case["message"], kb, client)

        assert answer.intent == case["expected_intent"]
        assert answer.citations == case["expected_citations"]

        print(f"\n[{case['id']}] question: {case['message']}")
        print(f"[{case['id']}] expected_answer: {case['expected_answer']}")
        print(f"[{case['id']}] actual reply:    {answer.reply}")
