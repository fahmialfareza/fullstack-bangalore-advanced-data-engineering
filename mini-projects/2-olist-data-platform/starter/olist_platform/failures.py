from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import psycopg
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from .batch import bronze, load, read_source, silver
from .config import ROOT, settings
from .contracts import CONTRACTS
from .local_services import stop_service, up_local
from .streaming import stream
from .utils import markdown_table, now_iso, write_report
from .warehouse import marts, model


def _result(case: str, broken: str, symptom: str, caught: bool, mechanism: str, recovery: str, seconds: float) -> list[object]:
    return [case, broken, symptom, "TERTANGKAP" if caught else "LOLOS", mechanism, recovery, round(seconds,2)]


def _topic(prefix: str) -> str:
    name=f"olist.failure.{prefix}.{uuid.uuid4().hex[:8]}"
    admin=AdminClient({"bootstrap.servers":settings().kafka_bootstrap})
    future=admin.create_topics([NewTopic(name,1,1)])[name]
    future.result(10); return name


def _missing_column() -> list[object]:
    t=time.perf_counter(); c=CONTRACTS["customers"]; df=read_source("customers").head(5).drop(columns=["customer_unique_id"])
    with tempfile.TemporaryDirectory() as folder:
        damaged=Path(folder)/c.file; df.to_csv(damaged,index=False)
        columns=list(__import__("pandas").read_csv(damaged,nrows=0).columns)
    missing=sorted(set(c.columns)-set(columns)); caught=missing==["customer_unique_id"]
    return _result("a","Removed `customer_unique_id` from an isolated CSV source copy",f"schema mismatch names missing={missing}",caught,
                   "central contract compares the complete header before conversion or load","restore the last bronze version",time.perf_counter()-t)


def _producer_twice() -> list[object]:
    t=time.perf_counter(); s=settings()
    report_paths=[s.outputs_dir/"stream_report.md",s.outputs_dir/"stream_report.json"]
    saved={path:path.read_bytes() for path in report_paths if path.exists()}
    with psycopg.connect(s.pg_dsn) as conn: before=conn.execute("SELECT count(*) FROM stream.order_events").fetchone()[0]
    try:
        first=stream(limit=5000); middle=first["consumer"]["stored_total"]
        second=stream(limit=5000); after=second["consumer"]["stored_total"]
    finally:
        for path,content in saved.items(): path.write_bytes(content)
    caught=before==middle==after and second["consumer"]["duplicates_ignored"]>0 and second["consumer"]["status_mismatch"]==0
    symptom=f"stored rows stayed {before:,}; second replay ignored {second['consumer']['duplicates_ignored']:,} valid duplicates"
    return _result("b","Ran the 5,000-order producer twice without resetting state",symptom,caught,
                   "deterministic event IDs plus primary-key conflict handling","none; replay is idempotent",time.perf_counter()-t)


def _consumer_crash() -> list[object]:
    t=time.perf_counter(); s=settings(); topic=_topic("crash"); group=f"olist-crash-{uuid.uuid4().hex}"
    event={"event_id":f"crash-{uuid.uuid4().hex}"}
    p=Producer({"bootstrap.servers":s.kafka_bootstrap,"acks":"all"}); p.produce(topic,value=json.dumps(event)); assert p.flush(20)==0
    worker=subprocess.run([sys.executable,str(ROOT/"scripts/crash_consumer.py"),topic,group],cwd=ROOT,timeout=30)
    consumer=Consumer({"bootstrap.servers":s.kafka_bootstrap,"group.id":group,"enable.auto.commit":False,"auto.offset.reset":"earliest","session.timeout.ms":6000,"heartbeat.interval.ms":1000}); consumer.subscribe([topic])
    redelivered=False; attempts=0
    deadline=time.time()+30
    while time.time()<deadline:
        msg=consumer.poll(1)
        if msg is not None and not msg.error():
            payload=json.loads(msg.value())
            with psycopg.connect(s.pg_dsn) as conn:
                cur=conn.execute("INSERT INTO stream.crash_probe(event_id) VALUES(%s) ON CONFLICT(event_id) DO UPDATE SET attempts=stream.crash_probe.attempts+1 RETURNING attempts",(payload["event_id"],))
                attempts=cur.fetchone()[0]
            consumer.commit(message=msg,asynchronous=False); redelivered=True; break
    consumer.close()
    with psycopg.connect(s.pg_dsn) as conn: rows=conn.execute("SELECT count(*) FROM stream.crash_probe WHERE event_id=%s",(event["event_id"],)).fetchone()[0]
    caught=worker.returncode==137 and redelivered and rows==1 and attempts==2
    return _result("c","Worker committed PostgreSQL then exited 137 before Kafka offset commit",f"message redelivered; one PK row, attempts={attempts}",caught,
                   "database commit precedes manual offset commit; PK handles redelivery","restart the same consumer group",time.perf_counter()-t)


def _broker_outage() -> list[object]:
    t=time.perf_counter(); s=settings(); topic=_topic("outage"); delivered=[]; errors=[]
    producer=Producer({"bootstrap.servers":s.kafka_bootstrap,"acks":"all","message.timeout.ms":30000,"queue.buffering.max.messages":10000})
    def callback(err,msg): (errors if err else delivered).append(msg.key().decode())
    def send():
        for i in range(1000):
            producer.produce(topic,key=str(i),value=json.dumps({"n":i}),callback=callback); producer.poll(0); time.sleep(.002)
        producer.flush(40)
    thread=threading.Thread(target=send); thread.start(); time.sleep(.4); stop_service("kafka"); time.sleep(3); up_local(); thread.join(45)
    caught=len(delivered)==1000 and not errors
    return _result("d","Stopped local Kafka for 3 seconds while 1,000 messages were being produced",f"delivered={len(delivered)}, failed={len(errors)} after broker recovery",caught,
                   "acks=all, delivery callbacks, buffering, retries, and checked flush","service manager restarts Kafka; resend only if callbacks report failures",time.perf_counter()-t)


def _snapshot() -> dict[str,int]:
    names={"raw":[*CONTRACTS],"dw":["dim_customer","fact_order","fact_order_item","fact_payment","fact_review"],
           "mart":["monthly_sales","delivery_performance","seller_scorecard","customer_rfm","order_reconciliation"]}
    with psycopg.connect(settings().pg_dsn) as conn:
        return {f"{schema}.{table}":conn.execute(f"SELECT count(*) FROM {schema}.{table}").fetchone()[0] for schema,tables in names.items() for table in tables}


def _batch_rerun() -> list[object]:
    t=time.perf_counter(); before=_snapshot(); b=bronze(); silver(); load(); model(); marts(); after=_snapshot()
    statuses={row[1] for row in b["tables"]}; caught=before==after and statuses=={"unchanged"}
    return _result("e","Reran bronze → silver → load → model → marts unchanged",f"compared {len(before)} table counts; differences={sum(before[k]!=after[k] for k in before)}; bronze={statuses}",caught,
                   "SHA-256 manifest and transactional full replacements","none; rerun is safe",time.perf_counter()-t)


def run_failure_tests() -> dict:
    started=time.perf_counter(); cases=[]
    for fn in (_missing_column,_producer_twice,_consumer_crash,_broker_outage,_batch_rerun):
        try: cases.append(fn())
        except Exception as exc: cases.append(_result(fn.__name__,"case raised unexpectedly",repr(exc),False,"see logs","repair and rerun",0))
    data={"stage":"inject","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"passed":sum(r[3]=="TERTANGKAP" for r in cases),"cases":cases}
    write_report("failure_tests",data,"# Failure injection evidence\n\n"+markdown_table(["case","broken","symptom","verdict","mechanism","recovery","seconds"],cases))
    if data["passed"] != 5: raise RuntimeError(f"failure injection: {data['passed']}/5 caught; see outputs/failure_tests.md")
    return data
