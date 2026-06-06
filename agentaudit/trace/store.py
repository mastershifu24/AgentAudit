import json
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path("traces.jsonl")


def append_span(record: dict[str, Any], log_path: Path = DEFAULT_LOG_PATH) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
