from enum import Enum

from pydantic import BaseModel


class Intent(str, Enum):
    HOURS = "hours"
    REFUND = "refund"
    PRODUCT = "product"
    OTHER = "other"


class Answer(BaseModel):
    intent: Intent
    reply: str
    citations: list[str]


def _check_grounding(answer: Answer, valid_filenames: set) -> None:
    """A domain rule about the KB, not a structural property of Answer —
    kept separate so Answer stays a pure data model."""
    unknown = [c for c in answer.citations if c not in valid_filenames]
    if unknown:
        raise ValueError(f"Citation(s) not in the knowledge base: {', '.join(unknown)}")

    expected_count = 0 if answer.intent == Intent.OTHER else 1
    if len(answer.citations) != expected_count:
        raise ValueError(
            f"Intent '{answer.intent}' must have exactly {expected_count} citation(s), got {len(answer.citations)}"
        )


def parse_response(json_text: str, valid_filenames: set) -> Answer:
    """Grounding checks are filename-level only — this confirms a citation
    names a real KB file, not that the reply's stated fact actually
    matches that file's content."""
    answer = Answer.model_validate_json(json_text)
    _check_grounding(answer, valid_filenames)
    return answer
