from __future__ import annotations

from datetime import date
from pathlib import Path


def save_report(report_dir: Path, today: date, markdown: str) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"morning-brief-{today.isoformat()}.md"
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    latest = report_dir / "latest.md"
    latest.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    return path
