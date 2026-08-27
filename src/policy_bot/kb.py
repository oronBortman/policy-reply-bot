from pathlib import Path


def load_kb(kb_dir: str | Path) -> dict:
    """Load knowledge base files from kb_dir, sorted by filename for
    deterministic ordering."""
    kb_dir = Path(kb_dir)
    kb_files = {}
    for file_path in sorted(kb_dir.glob("*.md")):
        filename = file_path.name
        content = file_path.read_text()
        kb_files[filename] = content

    return kb_files
