from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from collections import Counter
from pathlib import Path

import pandas as pd

from .config import settings
from .contracts import CONTRACTS, PG_TYPES
from .utils import markdown_table, now_iso, write_report


def read_source(name: str) -> pd.DataFrame:
    c = CONTRACTS[name]
    path = settings().raw_dir / c.file
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    missing = sorted(set(c.columns) - set(df.columns))
    extra = sorted(set(df.columns) - set(c.columns))
    if missing or extra:
        raise ValueError(f"schema mismatch {c.file}: missing={missing}, extra={extra}")
    return df[list(c.columns)]


def check() -> dict:
    rows = []
    ok = True
    for name, c in CONTRACTS.items():
        path = settings().raw_dir / c.file
        if not path.exists():
            rows.append([name, c.expected_rows, "-", "MISSING"]); ok = False; continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f); header = next(reader); count = sum(1 for _ in reader)
        status = "OK" if header == list(c.columns) and count == c.expected_rows else "FAIL"
        ok &= status == "OK"
        rows.append([name, c.expected_rows, count, status])
    data = {"stage": "check", "generated_at": now_iso(), "ok": ok, "tables": rows}
    write_report("dataset_check", data, "# Dataset check\n\n" + markdown_table(["table", "expected", "actual", "status"], rows))
    if not ok: raise RuntimeError("dataset check failed; see outputs/dataset_check.md")
    return data


def profile() -> dict:
    started = time.perf_counter(); frames = {n: read_source(n) for n in CONTRACTS}
    rows, details = [], {}
    for name, df in frames.items():
        c = CONTRACTS[name]
        duplicate_rows = int(df.duplicated().sum())
        unique_keys = None if not c.key else int(~df.duplicated(list(c.key)).any())
        nulls = {col: round(float((df[col] == "").mean() * 100), 3) for col in df}
        date_ranges = {}
        for col, typ in c.types.items():
            if typ == "timestamp":
                parsed = pd.to_datetime(df[col].replace("", pd.NA), errors="coerce")
                date_ranges[col] = [str(parsed.min()), str(parsed.max())]
        details[name] = {"rows": len(df), "exact_duplicates": duplicate_rows, "key": c.key,
                         "key_unique": unique_keys, "null_percent": nulls, "date_ranges": date_ranges}
        rows.append([name, len(df), duplicate_rows, "n/a" if unique_keys is None else ("yes" if unique_keys else "no"), max(nulls.values())])

    orders, customers = frames["orders"], frames["customers"]
    items, payments, reviews, geo = frames["order_items"], frames["order_payments"], frames["order_reviews"], frames["geolocation"]
    item_total = items.assign(total=pd.to_numeric(items.price) + pd.to_numeric(items.freight_value)).groupby("order_id").total.sum()
    pay_total = payments.assign(total=pd.to_numeric(payments.payment_value)).groupby("order_id").total.sum()
    reconciliation = pd.concat([item_total.rename("item"), pay_total.rename("paid")], axis=1).fillna(0)
    delta = (reconciliation.item - reconciliation.paid).abs()
    delivered = orders[orders.order_status == "delivered"]
    delivered_date = pd.to_datetime(delivered.order_delivered_customer_date, errors="coerce")
    carrier_date = pd.to_datetime(delivered.order_delivered_carrier_date, errors="coerce")
    lat, lng = pd.to_numeric(geo.geolocation_lat), pd.to_numeric(geo.geolocation_lng)
    findings = [
        [1, "customers", "customer_id counts orders, customer_unique_id counts people", int(customers.customer_id.nunique()), int(customers.customer_unique_id.nunique()), "use unique id in dim_customer"],
        [2, "customers", "people with multiple order-scoped customer IDs", int((customers.groupby("customer_unique_id").customer_id.nunique() > 1).sum()), "", "handle in DW"],
        [3, "orders", "orders without items", int((~orders.order_id.isin(items.order_id)).sum()), "", "retain with flag"],
        [4, "orders", "orders without payments", int((~orders.order_id.isin(payments.order_id)).sum()), "", "retain with flag"],
        [5, "reviews", "duplicate review_id rows", int(reviews.duplicated("review_id", keep=False).sum()), "", "deduplicate per order in DW"],
        [6, "reviews", "orders with multiple reviews", int((reviews.groupby("order_id").size() > 1).sum()), "", "choose latest answer"],
        [7, "geolocation", "exact duplicate rows", int(geo.duplicated().sum()), "", "aggregate in DW"],
        [8, "geolocation", "coordinates outside Brazil bounds", int((~lat.between(-34, 5) | ~lng.between(-74, -35)).sum()), "", "quarantine in silver"],
        [9, "orders", "delivered status missing delivery timestamp", int(delivered_date.isna().sum()), "", "soft rule; is_late null"],
        [10, "orders", "customer delivery earlier than carrier handoff", int((delivered_date < carrier_date).sum()), "", "soft rule; retain and report"],
        [11, "payments", "zero-value payments", int((pd.to_numeric(payments.payment_value) == 0).sum()), "", "soft rule; retain"],
        [12, "reconciliation", "orders differing by more than BRL 0.01", int((delta > .01).sum()), "", "classify in mart"],
        [13, "reconciliation", "orders differing by more than BRL 1.00", int((delta > 1).sum()), "", "classify in mart"],
    ]
    data = {"stage": "profile", "generated_at": now_iso(), "duration_seconds": round(time.perf_counter()-started, 3),
            "tables": details, "findings": findings}
    md = "# Automated profile\n\n" + markdown_table(["table", "rows", "exact duplicates", "natural key unique", "max null %"], rows)
    md += "\n\n## Numbered findings\n\n" + markdown_table(["#", "table", "finding", "count A", "count B", "decision"], findings)
    write_report("profile", data, md)
    return data


def _s3():
    import boto3
    s = settings()
    return boto3.client("s3", endpoint_url=s.minio_endpoint, aws_access_key_id=s.minio_access_key,
                        aws_secret_access_key=s.minio_secret_key, region_name="us-east-1")


def ensure_buckets() -> None:
    client = _s3(); existing = {x["Name"] for x in client.list_buckets().get("Buckets", [])}
    for bucket in ("bronze", "silver", "gold"):
        if bucket not in existing: client.create_bucket(Bucket=bucket)


def bronze() -> dict:
    started = time.perf_counter(); ensure_buckets(); client = _s3(); rows = []
    for name, c in CONTRACTS.items():
        path = settings().raw_dir / c.file
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_key = f"olist/{name}/manifest.json"
        try: manifest = json.loads(client.get_object(Bucket="bronze", Key=manifest_key)["Body"].read())
        except client.exceptions.NoSuchKey: manifest = {"table": name, "versions": []}
        previous = manifest["versions"][-1] if manifest["versions"] else None
        if previous and previous["sha256"] == digest:
            status, version = "unchanged", previous
        else:
            stamp = now_iso().replace(":", "-")
            key = f"olist/{name}/versions/{stamp}-{digest[:12]}.csv"
            client.upload_file(str(path), "bronze", key, ExtraArgs={"Metadata": {"sha256": digest}})
            with path.open(encoding="utf-8-sig", newline="") as f:
                count = sum(1 for _ in csv.reader(f)) - 1
            version = {"sha256": digest, "bytes": path.stat().st_size, "rows": count, "source": c.file,
                       "object": key, "ingested_at": now_iso()}
            manifest["versions"].append(version); manifest["latest"] = key
            client.put_object(Bucket="bronze", Key=manifest_key, Body=json.dumps(manifest, indent=2).encode(), ContentType="application/json")
            status = "uploaded" if previous is None else "new_version"
        rows.append([name, status, version["rows"], version["bytes"], version["sha256"][:12], version["object"]])
    data = {"stage":"bronze","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"tables":rows}
    write_report("bronze_report", data, "# Bronze ingest\n\n" + markdown_table(["table","status","rows","bytes","sha256","latest object"], rows))
    return data


def _convert(df: pd.DataFrame, name: str) -> pd.DataFrame:
    c = CONTRACTS[name]; out = df.copy()
    for col, typ in c.types.items():
        if typ == "zip": out[col] = out[col].str.zfill(5)
        elif typ == "timestamp": out[col] = pd.to_datetime(out[col].replace("", pd.NA), errors="coerce")
        elif typ == "numeric": out[col] = pd.to_numeric(out[col].replace("", pd.NA), errors="coerce")
        elif typ == "integer": out[col] = pd.to_numeric(out[col].replace("", pd.NA), errors="coerce").astype("Int64")
        else: out[col] = out[col].replace("", pd.NA)
    return out


def silver() -> dict:
    started=time.perf_counter(); s=settings(); s.silver_dir.mkdir(parents=True,exist_ok=True); s.quarantine_dir.mkdir(parents=True,exist_ok=True)
    source={n:read_source(n) for n in CONTRACTS}; converted={n:_convert(df,n) for n,df in source.items()}; rules=[]; table_rows=[]
    hard_masks: dict[str, list[tuple[str,pd.Series]]] = {}
    for name, df in converted.items():
        c=CONTRACTS[name]; masks=[]
        for key in c.key:
            masks.append((f"{key}_required", df[key].isna()))
        if c.key: masks.append(("natural_key_unique", df.duplicated(list(c.key), keep=False)))
        for col,typ in c.types.items():
            if typ in {"timestamp","numeric","integer"}:
                src_nonempty=source[name][col].ne(""); masks.append((f"{col}_parseable", src_nonempty & df[col].isna()))
            if typ=="zip": masks.append((f"{col}_five_digits", ~df[col].fillna("").str.fullmatch(r"\d{5}")))
        hard_masks[name]=masks
    geo=converted["geolocation"]
    hard_masks["geolocation"].append(("coordinates_inside_brazil", ~geo.geolocation_lat.between(-34,5) | ~geo.geolocation_lng.between(-74,-35)))
    pay=converted["order_payments"]; orders=converted["orders"]; reviews=converted["order_reviews"]
    soft = {
      "orders": [("missing_approval_timestamp", orders.order_approved_at.isna()), ("delivered_missing_delivery_timestamp", (orders.order_status=="delivered") & orders.order_delivered_customer_date.isna()), ("delivery_before_carrier", orders.order_delivered_customer_date < orders.order_delivered_carrier_date), ("unusual_status", ~orders.order_status.isin(["delivered","shipped","canceled","unavailable","invoiced","processing","created","approved"]))],
      "order_payments": [("zero_payment", pay.payment_value==0), ("negative_payment", pay.payment_value<0)],
      "order_reviews": [("score_outside_1_5", ~reviews.review_score.between(1,5)), ("empty_comment", reviews.review_comment_message.isna())],
      "products": [("missing_category", converted["products"].product_category_name.isna())],
    }
    ensure_buckets(); client=_s3()
    for name,df in converted.items():
        reasons=pd.Series([[] for _ in range(len(df))],index=df.index,dtype=object)
        for rule,mask in hard_masks[name]:
            mask=mask.fillna(False); count=int(mask.sum()); rules.append([name,rule,"hard",count,"quarantine"])
            reasons.loc[mask]=reasons.loc[mask].map(lambda xs,r=rule:[*xs,r])
        for rule,mask in soft.get(name,[]): rules.append([name,rule,"soft",int(mask.fillna(False).sum()),"report"])
        bad=reasons.str.len()>0; ratio=float(bad.mean()); verdict="FAIL" if ratio>.02 else ("PASS+QUARANTINE" if bad.any() else "PASS")
        quarantine=df.loc[bad].copy(); quarantine["_dq_reasons"]=reasons.loc[bad].map(lambda x:",".join(x))
        clean=df.loc[~bad].copy()
        if verdict=="FAIL": raise RuntimeError(f"silver gate FAIL for {name}: {bad.sum()}/{len(df)} ({ratio:.2%}) exceeds 2%")
        clean.to_parquet(s.silver_dir/f"{name}.parquet",index=False); quarantine.to_parquet(s.quarantine_dir/f"{name}.parquet",index=False)
        client.upload_file(str(s.silver_dir/f"{name}.parquet"),"silver",f"olist/{name}/data.parquet")
        client.upload_file(str(s.quarantine_dir/f"{name}.parquet"),"silver",f"olist/{name}/quarantine.parquet")
        table_rows.append([name,len(df),len(clean),int(bad.sum()),f"{ratio:.3%}",verdict])
    data={"stage":"silver","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"threshold":.02,"tables":table_rows,"rules":rules}
    md="# Silver quality gate\n\nThreshold: **2% hard-rule quarantine per table**. Above it, the table is not loaded.\n\n"+markdown_table(["table","source","silver","quarantine","ratio","verdict"],table_rows)+"\n\n## Rules\n\n"+markdown_table(["table","rule","type","violations","action"],rules)
    write_report("dq_report",data,md); return data


def load() -> dict:
    import psycopg
    started=time.perf_counter(); rows=[]; s=settings()
    with psycopg.connect(s.pg_dsn) as conn:
      with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for name,c in CONTRACTS.items():
            df=pd.read_parquet(s.silver_dir/f"{name}.parquet")
            cols=", ".join(f'"{col}" {PG_TYPES[c.types[col]]}' for col in c.columns)
            cur.execute(f'DROP TABLE IF EXISTS raw."{name}" CASCADE')
            cur.execute(f'CREATE TABLE raw."{name}" ({cols})')
            buffer=io.StringIO(); df.to_csv(buffer,index=False,header=False,na_rep="\\N"); buffer.seek(0)
            quoted=", ".join(f'"{x}"' for x in c.columns)
            with cur.copy(f'COPY raw."{name}" ({quoted}) FROM STDIN WITH (FORMAT CSV, NULL \'\\N\')') as cp:
                while chunk:=buffer.read(1024*1024): cp.write(chunk)
            if c.key: cur.execute(f'ALTER TABLE raw."{name}" ADD PRIMARY KEY ({quoted if len(c.key)==len(c.columns) else ", ".join(chr(34)+x+chr(34) for x in c.key)})')
            rows.append([name,len(df)])
    data={"stage":"load","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"tables":rows}
    write_report("load_report",data,"# PostgreSQL raw load\n\nAll tables are replaced inside one transaction.\n\n"+markdown_table(["table","rows"],rows)); return data
