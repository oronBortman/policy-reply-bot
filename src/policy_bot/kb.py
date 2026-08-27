from pathlib import Path


def load_kb():
    """Load knowledge base files from data/kb directory.

    Returns:
        dict: A dictionary mapping filename to file content,
              sorted by filename for deterministic ordering.
    """
    kb_dir = Path("data") / "kb"

    kb_files = {}
    for file_path in sorted(kb_dir.glob("*.md")):
        filename = file_path.name
        content = file_path.read_text()
        kb_files[filename] = content

    return kb_files
