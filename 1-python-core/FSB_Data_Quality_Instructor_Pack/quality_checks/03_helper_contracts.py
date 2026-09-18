from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.cleaners import (
    normalize_text,
    normalize_email,
    parse_non_negative_float,
    parse_positive_int,
)

CASES = [
    ("text None", lambda: normalize_text(None), None),
    ("text trim", lambda: normalize_text("  Rani  "), "Rani"),
    ("text empty", lambda: normalize_text("   "), None),
    ("email normalize", lambda: normalize_email(" RANI@MAIL.COM "), "rani@mail.com"),
    ("email invalid", lambda: normalize_email("rani-at-mail"), None),
    ("price string", lambda: parse_non_negative_float("19.5"), 19.5),
    ("price negative", lambda: parse_non_negative_float(-1), None),
    ("quantity string", lambda: parse_positive_int("2"), 2),
    ("quantity zero", lambda: parse_positive_int(0), None),
    ("quantity decimal", lambda: parse_positive_int(2.5), None),
    ("quantity bool", lambda: parse_positive_int(True), None),
]

failures = 0
for name, function, expected in CASES:
    try:
        actual = function()
        passed = actual == expected
    except Exception as exc:
        actual = f"{type(exc).__name__}: {exc}"
        passed = False
    print("PASS" if passed else "FAIL", name, "=>", actual)
    failures += int(not passed)

print(f"\n{len(CASES) - failures}/{len(CASES)} helper cases passed")
raise SystemExit(1 if failures else 0)
