from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.cleaners import clean_users,clean_products,clean_transactions
SPECS={"users":(clean_users,14,2,"user_id"),"products":(clean_products,10,2,"product_id"),"transactions":(clean_transactions,12,3,"tx_id")}
REQUIRED={"entity","id","field","raw","action","clean","reason"}; failed=False
for name,(fn,a,b,id_field) in SPECS.items():
    rows=json.loads((ROOT/f"data/raw/{name}.json").read_text(encoding="utf-8"))
    clean,rejected,decisions=fn(rows); ids=[r.get(id_field) for r in clean]
    checks={"counts":len(clean)==a and len(rejected)==b,"conservation":len(rows)==len(clean)+len(rejected),"unique IDs":all(ids) and len(ids)==len(set(ids)),"reasons":all(r.get("reason") for r in rejected),"log schema":all(REQUIRED<=set(d) for d in decisions)}
    ok=all(checks.values()); failed |= not ok
    print("PASS" if ok else "FAIL",name,checks)
raise SystemExit(1 if failed else 0)
