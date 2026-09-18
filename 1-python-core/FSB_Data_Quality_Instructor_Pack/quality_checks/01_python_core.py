from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.foundations import clean_name, safe_city, classify_quantity, numbered_names, parse_quantity

CASES = [
    ("string assign", lambda: clean_name("  rani  "), "Rani"),
    ("dict existing key", lambda: safe_city({"city": "Bandung"}), "Bandung"),
    ("dict fallback", lambda: safe_city({"name": "Rani"}), "Unknown"),
    ("quantity int", lambda: classify_quantity(12), "positive-int"),
    ("quantity string", lambda: classify_quantity("12"), "numeric-string"),
    ("quantity invalid", lambda: classify_quantity("two"), "invalid"),
    ("enumerate", lambda: numbered_names(["Rani", "Bima"]), [(1,"Rani"),(2,"Bima")]),
    ("try except", lambda: [parse_quantity("2"), parse_quantity("two"), parse_quantity(None)], [2,None,None]),
]
failed=0
for name,fn,expected in CASES:
    try:
        actual=fn(); ok=actual==expected
    except Exception as exc:
        actual=f"{type(exc).__name__}: {exc}"; ok=False
    print("PASS" if ok else "FAIL", name, "=>", actual)
    failed += int(not ok)
print(f"\n{len(CASES)-failed}/{len(CASES)} core cases passed")
raise SystemExit(1 if failed else 0)
