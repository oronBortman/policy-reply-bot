import uuid


def random_string() -> str:
    return uuid.uuid4().hex
