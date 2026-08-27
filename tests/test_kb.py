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


def test_load_kb_sorts_files_created_in_non_alphabetical_order(tmp_path):
    """Result order is alphabetical by filename even when files were created
    on disk in a different order — proves the sort is real, not incidental
    (a naive glob() without sorted() could coincidentally match alphabetical
    order on filesystems that return entries in creation order, but not
    when creation order is deliberately scrambled like this)."""
    (tmp_path / "c.md").write_text("c content")
    (tmp_path / "a.md").write_text("a content")
    (tmp_path / "b.md").write_text("b content")

    kb = load_kb(tmp_path)

    assert list(kb.keys()) == ["a.md", "b.md", "c.md"]


def test_load_kb_raises_on_empty_kb_directory(tmp_path):
    """An existing but empty KB directory (zero .md files) raises rather
    than silently returning {} — every other component in this codebase
    fails closed on a bad state, and load_kb should too."""
    with pytest.raises(FileNotFoundError):
        load_kb(tmp_path)


def test_load_kb_raises_on_missing_kb_directory(tmp_path):
    """A KB directory that doesn't exist at all raises rather than
    silently returning {}."""
    missing_dir = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        load_kb(missing_dir)


def test_load_kb_accepts_a_string_path_not_just_path_object():
    """load_kb accepts kb_dir as a plain string too, not only pathlib.Path
    — so a future caller (env var, CLI flag) can pass a raw string without
    wrapping it first."""
    kb = load_kb(str(KB_DIR))
    assert list(kb.keys()) == KB_FILENAMES
