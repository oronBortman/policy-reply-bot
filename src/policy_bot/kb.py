from pathlib import Path


def load_kb(kb_dir: str | Path) -> dict:
    """Load knowledge base files from kb_dir, sorted by filename for
    deterministic ordering.

    Raises:
        FileNotFoundError: If kb_dir doesn't exist or contains no .md
            files. A missing/empty KB is a bad state, not a valid empty
            answer, so this fails closed instead of silently returning {}.
    """
    kb_dir = Path(kb_dir)
    kb_files = {}
    for file_path in sorted(kb_dir.glob("*.md")):
        filename = file_path.name
        content = file_path.read_text()
        kb_files[filename] = content

    if not kb_files:
        raise FileNotFoundError(
            f"No .md files found in KB directory: {kb_dir}"
        )

    return kb_files
