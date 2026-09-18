import json
from pathlib import Path
def read_json(path):
    with Path(path).open(encoding="utf-8") as f:return json.load(f)
def write_json(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
