from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_report(name: str, data: dict, markdown: str) -> None:
    out = settings().outputs_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    (out / f"{name}.md").write_text(markdown.rstrip() + "\n", encoding="utf-8")


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |" for row in rows]
    return "\n".join(lines)
