from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

FILE = Path(r"C:\Users\victo\Desktop\ADMINISTRATIF\VICTOR\PROJET\CODAGE\DASHMONEY\data\transactions.jsonl")


def migrate_line(obj: dict) -> dict:
    kind = obj.get("kind")

    if kind == "INVESTMENT":
        obj["kind"] = "TRANSFER"
        # garder la category si déjà pertinente, sinon forcer INVESTMENT
        cat = obj.get("category")
        if not isinstance(cat, str) or not cat.strip():
            obj["category"] = "INVESTMENT"
        return obj

    if kind == "ADJUSTMENT":
        # amount est stocké en string
        amt = Decimal(obj["amount"])
        obj["kind"] = "INCOME" if amt > 0 else "EXPENSE"
        obj["category"] = "ADJUSTMENT"
        return obj

    return obj


def main() -> None:
    if not FILE.exists():
        raise SystemExit(f"File not found: {FILE.resolve()}")

    lines = FILE.read_text(encoding="utf-8").splitlines()
    out_lines: list[str] = []
    changed = 0

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        before = obj.get("kind")
        obj2 = migrate_line(obj)
        after = obj2.get("kind")
        if before != after:
            changed += 1
            print(f"line {line_no}: kind {before} -> {after}")
        out_lines.append(json.dumps(obj2, ensure_ascii=False))

    backup = FILE.with_suffix(".jsonl.bak")
    backup.write_text("\n".join(lines) + "\n", encoding="utf-8")
    FILE.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"Done. Changed {changed} lines.")
    print(f"Backup: {backup.name}")


if __name__ == "__main__":
    main()