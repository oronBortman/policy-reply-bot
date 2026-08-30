import pytest
from pathlib import Path
from policy_bot.kb import load_kb


KB_FILENAMES = ["hours.md", "products.md", "refunds.md"]


def test_load_kb_returns_all_three_filenames():
    """Loading the KB directory returns all three filenames (hours, products, refunds)."""
    kb = load_kb()
    for filename in KB_FILENAMES:
        assert filename in kb


def test_load_kb_content_matches_disk():
    """Loaded content matches what's actually on disk for each file."""
    kb = load_kb()

    kb_dir = Path(__file__).parent.parent / "data" / "kb"

    for filename in KB_FILENAMES:
        file_path = kb_dir / filename
        expected_content = file_path.read_text()
        assert kb[filename] == expected_content


def test_load_kb_result_sorted_by_filename():
    """Result order is deterministic — sorted by filename — so prompt output is stable across runs."""
    kb = load_kb()

    assert list(kb.keys()) == KB_FILENAMES
