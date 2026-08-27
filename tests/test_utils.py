import uuid


def random_string() -> str:
    """An arbitrary string for fields a test doesn't assert on — signals
    to the reader that the exact value carries no meaning."""
    return uuid.uuid4().hex
