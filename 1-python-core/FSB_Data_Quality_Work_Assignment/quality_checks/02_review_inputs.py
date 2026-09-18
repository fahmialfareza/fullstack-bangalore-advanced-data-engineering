import json
from pathlib import Path
for p in sorted(Path("data/raw").glob("*.json")):
 x=json.load(p.open(encoding="utf-8"));print(p.name,type(x).__name__,len(x));print("first",x[0]);print("fields",sorted(x[0]))
