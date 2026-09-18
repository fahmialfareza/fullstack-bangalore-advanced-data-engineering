from src.io_utils import read_json, write_json
from src.cleaners import clean_users, clean_products, clean_transactions

PIPELINES = [
    ("users", clean_users),
    ("products", clean_products),
    ("transactions", clean_transactions),
]

def main():
    decisions = []
    incomplete = []
    for name, cleaner in PIPELINES:
        raw = read_json(f"data/raw/{name}.json")
        try:
            clean, rejected, log = cleaner(raw)
        except NotImplementedError as exc:
            print(f"[PENDING] {name}: {exc}")
            incomplete.append(name)
            continue
        write_json(f"data/processed/{name}.json", clean)
        write_json(f"data/processed/{name}_rejected.json", rejected)
        decisions.extend(log)
        print(f"[OK] {name}: raw={len(raw)} clean={len(clean)} rejected={len(rejected)}")
    write_json("data/processed/decision_log.json", decisions)
    if incomplete:
        print("\nPipeline incomplete:", ", ".join(incomplete))
        raise SystemExit(1)

if __name__ == "__main__":
    main()
