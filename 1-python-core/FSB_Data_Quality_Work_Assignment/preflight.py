from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
checks = []

def check(label, condition, detail=""):
    checks.append(bool(condition))
    status = "PASS" if condition else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"{status:4} {label}{suffix}")

check("Python 3.11+", sys.version_info >= (3, 11), sys.version.split()[0])
check("Root project", (ROOT / "src" / "cleaners.py").exists(), str(ROOT))

for name in ("users", "products", "transactions"):
    path = ROOT / "data" / "raw" / f"{name}.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        check(f"Raw {name}", isinstance(rows, list) and len(rows) > 0, f"{len(rows)} rows")
    except Exception as exc:
        check(f"Raw {name}", False, f"{type(exc).__name__}: {exc}")

try:
    import src.cleaners as cleaners
    check("Import src.cleaners", True, str(Path(cleaners.__file__).resolve()))
except Exception as exc:
    check("Import src.cleaners", False, f"{type(exc).__name__}: {exc}")

print("\nREADY TO LEARN" if all(checks) else "\nFIX SETUP BEFORE CLASS")
raise SystemExit(0 if all(checks) else 1)
