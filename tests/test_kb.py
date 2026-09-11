import pytest
from pathlib import Path
from policy_bot.kb import load_kb


# KB directory path resolved from test file location
KB_DIR = Path(__file__).parent.parent / "data" / "kb"
KB_FILENAMES = ["hours.md", "products.md", "refunds.md"]


def test_load_kb_returns_all_three_filenames():
    """Loading the KB directory returns all three filenames (hours, products, refunds)."""
    kb = load_kb(KB_DIR)
    for filename in KB_FILENAMES:
        assert filename in kb


def test_load_kb_content_matches_disk():
    """Loaded content matches what's actually on disk for each file."""
    kb = load_kb(KB_DIR)

    for filename in KB_FILENAMES:
        file_path = KB_DIR / filename
        expected_content = file_path.read_text()
        assert kb[filename] == expected_content


def test_load_kb_result_sorted_by_filename():
    """Result order is deterministic — sorted by filename — so prompt output is stable across runs."""
    kb = load_kb(KB_DIR)

    assert list(kb.keys()) == KB_FILENAMES


def test_load_kb_accepts_a_string_path_not_just_path_object():
    """load_kb accepts kb_dir as a plain string too, not only pathlib.Path
    — so a future caller (env var, CLI flag) can pass a raw string without
    wrapping it first."""
    kb = load_kb(str(KB_DIR))
    assert list(kb.keys()) == KB_FILENAMES
