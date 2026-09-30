"""Write JSON output files."""

import json
import os
from pathlib import Path


def write_json(path: Path, data) -> None:
    """Replace path with data as pretty UTF-8 JSON.

    The file is always rewritten, never appended to, so a rerun gives the same
    file instead of doubling it. Writing to a temporary file first means a
    crash mid-write never leaves a half-written file behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp_path, path)
