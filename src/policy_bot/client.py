import logging
import time
from enum import Enum

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


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


DEFAULT_MODEL = "claude-sonnet-5"

_ASSISTANT_PREFILL = "{"


def build_system_prompt(kb: dict) -> str:
    """Build the system prompt from the loaded knowledge base plus the
    JSON-output instructions the model must follow.

    Includes every KB file's name and full content verbatim, plus rules for:
    - the required JSON output shape (intent/reply/citations),
    - the valid intent values and citation-count rules,
    - the "topic covered but specific item not found" case (e.g. "do you
      sell shoes?" when only backpacks/jackets/stoves are listed): the model
      must still use that topic's intent, still cite that topic's file (it
      was consulted to determine the item isn't there), and say in the
      reply that the specific item isn't carried.

    Args:
        kb: Mapping of filename to file content, as returned by load_kb().

    Returns:
        str: The full system prompt to send with every API call.
    """
    kb_sections = [f"### {filename}\n{content}" for filename, content in kb.items()]
    kb_text = "\n\n".join(kb_sections)

    return f"""You are a customer support assistant for an online shop. Answer only using the knowledge base below. Never invent facts that are not in it.

Knowledge base:
{kb_text}

Respond with a single JSON object with exactly these fields:
- "intent": one of "hours", "refund", "product", "other"
- "reply": a direct, natural-language answer to the customer's question
- "citations": a list of knowledge-base filenames that support the reply

Rules:
- If intent is "other", citations must be an empty list.
- For any other intent, citations must contain exactly one filename, the file the answer is grounded in.
- If the customer's question is about a topic covered by one of the files above (hours, refunds, or products) but asks about a specific item that is not listed there (for example "do you sell shoes?" when only backpacks, jackets, and stoves are listed), still use that topic's intent, still cite that topic's file (it was consulted to determine the item isn't there), and state in the reply that the specific item isn't carried.
- If the question is unrelated to any topic in the knowledge base, use intent "other" with an empty citations list, and politely say you can't help with that — never guess.
- Output raw JSON only. No markdown code fences, no prose before or after the JSON.
"""


def answer_question(question: str, kb: dict, client, model: str = DEFAULT_MODEL) -> Answer:
    """Answer a customer question using the injected Anthropic-style client.

    Builds the system prompt from `kb`, calls `client.messages.create(...)`
    with max_tokens=1024 and temperature=0 (passed via extra_body, since the
    installed anthropic SDK's typed Messages.create() signature has no
    temperature parameter), and prefills the assistant turn
    with an opening "{" so the model continues directly as JSON (reducing
    the chance it wraps its answer in prose or markdown fences). The prefill
    is prepended back onto the model's continuation before parsing, since
    the API response only contains the continuation, not the prefill text.
    Latency and token usage are logged for every call. The reconstructed
    JSON is parsed and grounding-validated via parse_response() before
    being returned.

    Args:
        question: The customer's raw question text.
        kb: Mapping of filename to file content, as returned by load_kb().
        client: Any object exposing `.messages.create(...)` matching the
            Anthropic SDK's Messages API shape (injected dependency, so
            tests can pass a mock and make zero live network calls).
        model: Model identifier to request.

    Returns:
        Answer: The validated answer.

    Raises:
        ValueError: If the model's JSON is malformed, missing a field, or
            fails grounding validation (see parse_response()).
    """
    system_prompt = build_system_prompt(kb)
    messages = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": _ASSISTANT_PREFILL},
    ]

    start = time.monotonic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        extra_body={"temperature": 0},
        system=system_prompt,
        messages=messages,
    )
    latency = time.monotonic() - start

    usage = response.usage
    logger.info(
        "policy_bot API call: model=%s latency=%.3fs input_tokens=%s output_tokens=%s",
        model,
        latency,
        usage.input_tokens,
        usage.output_tokens,
    )

    raw_json = _ASSISTANT_PREFILL + response.content[0].text
    valid_filenames = set(kb.keys())
    return parse_response(raw_json, valid_filenames)
