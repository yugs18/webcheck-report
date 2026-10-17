import json
from datetime import datetime, timezone
from pathlib import Path

def create_report(result: dict) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


def save_report(report: dict, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")
