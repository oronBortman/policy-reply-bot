from enum import Enum

from pydantic import BaseModel, ValidationError


class Intent(str, Enum):
    HOURS = "hours"
    REFUND = "refund"
    PRODUCT = "product"
    OTHER = "other"


class Answer(BaseModel):
    """A validated response from the model. Pure structure only — no
    knowledge of the knowledge base. See _check_grounding() for that."""
    intent: Intent
    reply: str
    citations: list[str]


def _check_grounding(answer: Answer, valid_filenames: set) -> None:
    """A citation not in the knowledge base, or a citation count that
    doesn't match the intent, is a grounding failure — a domain rule about
    the KB, not a structural property of Answer itself.

    Raises:
        ValueError: if a citation names a file outside valid_filenames, or
            citation count doesn't match intent (0 for "other", 1 otherwise).
    """
    unknown = [c for c in answer.citations if c not in valid_filenames]
    if unknown:
        raise ValueError(f"Citation(s) not in the knowledge base: {', '.join(unknown)}")

    expected_count = 0 if answer.intent == Intent.OTHER else 1
    if len(answer.citations) != expected_count:
        raise ValueError(
            f"Intent '{answer.intent}' must have exactly {expected_count} citation(s), got {len(answer.citations)}"
        )


def parse_response(json_text: str, valid_filenames: set) -> Answer:
    """Parse and validate a JSON response from the model.

    Raises:
        ValueError: if JSON is malformed, a required field is missing, intent
            is invalid, citations reference non-existent files, or citation
            count doesn't match intent. Grounding checks are filename-level
            only — this confirms a citation names a real KB file, not that
            the reply's stated fact actually matches that file's content.
    """
    try:
        answer = Answer.model_validate_json(json_text)
    except ValidationError as e:
        raise ValueError(str(e)) from e

    _check_grounding(answer, valid_filenames)
    return answer
