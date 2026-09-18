from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cleaners import clean_users

rows = json.loads((ROOT / "data/raw/users.json").read_text(encoding="utf-8"))
clean, rejected, decisions = clean_users(rows)
by_id = {row["user_id"]: row for row in clean}
actions = {item.get("action") for item in decisions}

checks = {
    "count clean": len(clean) == 14,
    "count rejected": len(rejected) == 2,
    "conservation": len(rows) == len(clean) + len(rejected),
    "unique IDs": len(by_id) == len(clean),
    "U001 ID trimmed": "U001" in by_id,
    "U001 email normalized": by_id.get("U001", {}).get("email") == "rani@mail.com",
    "U003 invalid email null": by_id.get("U003", {}).get("email") is None,
    "reasons present": all(item.get("reason") for item in rejected),
    "decision actions": {"DROP", "FIX", "NULL"} <= actions,
}

for label, passed in checks.items():
    print("PASS" if passed else "FAIL", label)

print(f"\nusers: raw={len(rows)} clean={len(clean)} rejected={len(rejected)}")
raise SystemExit(0 if all(checks.values()) else 1)
