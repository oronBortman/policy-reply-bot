import os
import sys
import json
from pathlib import Path
import anthropic

from policy_bot.kb import load_kb
from policy_bot.client import answer_question


def main():
    """CLI entry point: read a message from argv, call the policy bot, print JSON output."""
    if len(sys.argv) < 2:
        print("Usage: cli <message>", file=sys.stderr)
        sys.exit(1)

    message = sys.argv[1]

    # anthropic.Anthropic() constructs fine with no key; the SDK only fails
    # later, at request-build time, with a raw TypeError. Check upfront so
    # we can give a clear error instead.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(1)

    # cli.py is at src/policy_bot/cli.py; two parent levels up is the repo root
    kb_dir = Path(__file__).resolve().parents[2] / "data" / "kb"

    try:
        kb = load_kb(kb_dir)
        client = anthropic.Anthropic()
        answer = answer_question(message, kb, client)

        result = {
            "intent": answer.intent,
            "reply": answer.reply,
            "citations": answer.citations,
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    except (ValueError, anthropic.APIError, IndexError, AttributeError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
