from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
SPECS = {
    "users": {"clean": 14, "rejected": 2, "id": "user_id"},
    "products": {"clean": 10, "rejected": 2, "id": "product_id"},
    "transactions": {"clean": 12, "rejected": 3, "id": "tx_id"},
}

failures = []
loaded = {}

for name, spec in SPECS.items():
    clean_path = ROOT / f"data/processed/{name}.json"
    rejected_path = ROOT / f"data/processed/{name}_rejected.json"

    if not clean_path.exists() or not rejected_path.exists():
        print("FAIL", name, "missing processed/rejected output")
        failures.append(name)
        continue

    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    raw = json.loads((ROOT / f"data/raw/{name}.json").read_text(encoding="utf-8"))
    ids = [row.get(spec["id"]) for row in clean]

    checks = {
        "clean count": len(clean) == spec["clean"],
        "rejected count": len(rejected) == spec["rejected"],
        "conservation": len(raw) == len(clean) + len(rejected),
        "IDs present": all(ids),
        "IDs unique": len(ids) == len(set(ids)),
        "reject reasons": all(item.get("reason") for item in rejected),
    }

    passed = all(checks.values())
    print("PASS" if passed else "FAIL", name, checks)
    if not passed:
        failures.append(name)
    loaded[name] = clean

if "users" in loaded:
    users = {row["user_id"]: row for row in loaded["users"]}
    semantic_checks = {
        "U001 exists": "U001" in users,
        "U001 normalized email": users.get("U001", {}).get("email") == "rani@mail.com",
        "U003 invalid email null": users.get("U003", {}).get("email") is None,
    }
    passed = all(semantic_checks.values())
    print("PASS" if passed else "FAIL", "user semantics", semantic_checks)
    if not passed:
        failures.append("user semantics")

if "transactions" in loaded:
    quantity_ok = all(
        isinstance(row.get("quantity"), int)
        and not isinstance(row.get("quantity"), bool)
        and row["quantity"] > 0
        for row in loaded["transactions"]
    )
    print("PASS" if quantity_ok else "FAIL", "transaction quantities")
    if not quantity_ok:
        failures.append("transaction quantities")

log_path = ROOT / "data/processed/decision_log.json"
actions = set()
if log_path.exists():
    decisions = json.loads(log_path.read_text(encoding="utf-8"))
    actions = {item.get("action") for item in decisions}
required_log_keys = {"entity", "id", "field", "raw", "action", "clean", "reason"}
log_schema_ok = log_path.exists() and all(required_log_keys <= set(item) for item in decisions)
action_ok = {"DROP", "FIX", "NULL"} <= actions and log_schema_ok
print("PASS" if action_ok else "FAIL", "decision actions/schema", actions)
if not action_ok:
    failures.append("decision log")

print("\nREADY FOR REVIEW" if not failures else f"\nNOT COMPLETE: {', '.join(failures)}")
raise SystemExit(0 if not failures else 1)
