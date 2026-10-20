from __future__ import annotations

import hashlib
import json
import random
import time
from datetime import datetime, timezone

import psycopg
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from .config import settings
from .utils import markdown_table, now_iso, write_report

STATUS_RANK = {"created": 10, "approved": 20, "invoiced": 25, "processing": 30, "shipped": 40,
               "delivered": 50, "unavailable": 90, "canceled": 100}


def event_id(order_id: str, status: str) -> str:
    return hashlib.sha256(f"{order_id}:{status}".encode()).hexdigest()


def make_events(row: dict) -> list[dict]:
    candidates = [("created", row["order_purchase_timestamp"]), ("approved", row["order_approved_at"]),
                  ("shipped", row["order_delivered_carrier_date"]), ("delivered", row["order_delivered_customer_date"])]
    final = row["order_status"]
    if final not in {status for status, _ in candidates}:
        candidates.append((final, row["order_approved_at"] or row["order_purchase_timestamp"]))
    result = []
    for status, timestamp in candidates:
        if timestamp and STATUS_RANK.get(status, 0) <= STATUS_RANK.get(final, 100):
            result.append({"event_id": event_id(row["order_id"], status), "order_id": row["order_id"],
                           "status": status, "status_rank": STATUS_RANK.get(status, 0),
                           "event_ts": timestamp.isoformat(), "produced_at": now_iso()})
    if not any(x["status"] == final for x in result):
        result.append({"event_id": event_id(row["order_id"], final), "order_id": row["order_id"],
                       "status": final, "status_rank": STATUS_RANK.get(final, 0),
                       "event_ts": (row["order_purchase_timestamp"]).isoformat(), "produced_at": now_iso()})
    return result


def validate(payload: object) -> tuple[bool, str]:
    if not isinstance(payload, dict): return False, "payload_not_object"
    missing = sorted({"event_id","order_id","status","status_rank","event_ts","produced_at"} - payload.keys())
    if missing: return False, "missing_fields:" + ",".join(missing)
    try: datetime.fromisoformat(str(payload["event_ts"])); datetime.fromisoformat(str(payload["produced_at"]))
    except ValueError: return False, "invalid_timestamp"
    if payload["status"] not in STATUS_RANK: return False, "unknown_status"
    return True, ""


def ensure_topics() -> None:
    s=settings(); admin=AdminClient({"bootstrap.servers":s.kafka_bootstrap,"client.id":"olist-admin"})
    existing=set(admin.list_topics(timeout=10).topics)
    missing=[NewTopic(topic,num_partitions=3,replication_factor=1) for topic in (s.kafka_topic,s.kafka_dlq_topic) if topic not in existing]
    for future in admin.create_topics(missing).values() if missing else []: future.result(10)


def _schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS stream")
        cur.execute("""CREATE TABLE IF NOT EXISTS stream.order_events(
          event_id text PRIMARY KEY,order_id text NOT NULL,status text NOT NULL,status_rank int NOT NULL,
          event_ts timestamp NOT NULL,produced_at timestamptz NOT NULL,consumed_at timestamptz NOT NULL DEFAULT now(),out_of_order boolean NOT NULL DEFAULT false)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS stream.order_current(
          order_id text PRIMARY KEY,status text NOT NULL,status_rank int NOT NULL,event_ts timestamp NOT NULL,event_id text NOT NULL)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS stream.order_dlq(
          id bigserial PRIMARY KEY,payload text NOT NULL,reason text NOT NULL,received_at timestamptz NOT NULL DEFAULT now())""")


def stream(limit: int | None = None) -> dict:
    started=time.perf_counter(); s=settings(); ensure_topics(); rng=random.Random(20261020)
    with psycopg.connect(s.pg_dsn) as conn:
        _schema(conn)
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT * FROM raw.orders ORDER BY order_id" + (" LIMIT %s" if limit else ""), ([limit] if limit else []))
            events=[event for row in cur.fetchall() for event in make_events(row)]
    producer=Producer({"bootstrap.servers":s.kafka_bootstrap,"acks":"all","message.send.max.retries":8,"queue.buffering.max.messages":1000000})
    duplicates=late=corrupt=0; delayed=[]; futures=[]
    for event in events:
        if rng.random()<.02: delayed.append(event); late+=1
        else: producer.produce(s.kafka_topic,key=event["order_id"],value=json.dumps(event)); producer.poll(0)
        if rng.random()<.03: producer.produce(s.kafka_topic,key=event["order_id"],value=json.dumps(event)); duplicates+=1
        if rng.random()<.005:
            bad=dict(event); bad.pop("event_ts"); producer.produce(s.kafka_topic,key=event["order_id"],value=json.dumps(bad)); corrupt+=1
    for event in reversed(delayed): producer.produce(s.kafka_topic,key=event["order_id"],value=json.dumps(event))
    if producer.flush(60): raise RuntimeError("Kafka producer still has undelivered messages")

    consumer=Consumer({"bootstrap.servers":s.kafka_bootstrap,"group.id":s.kafka_group,"enable.auto.commit":False,"auto.offset.reset":"earliest"})
    consumer.subscribe([s.kafka_topic]); dlq=Producer({"bootstrap.servers":s.kafka_bootstrap,"acks":"all"})
    consumed=new=duplicate_count=out_of_order=dlq_count=0
    with psycopg.connect(s.pg_dsn) as conn:
      _schema(conn)
      idle_since=time.monotonic(); assigned=False; last_msg=None; pending=0
      while (not assigned or time.monotonic()-idle_since<5):
        msg=consumer.poll(1)
        has_assignment=bool(consumer.assignment())
        if has_assignment and not assigned:
            assigned=True
            idle_since=time.monotonic()
        if msg is None: continue
        if msg.error(): raise RuntimeError(msg.error())
        idle_since=time.monotonic(); consumed+=1; last_msg=msg; pending+=1
        try: payload=json.loads(msg.value().decode())
        except Exception: payload=msg.value().decode(errors="replace")
        valid,reason=validate(payload)
        if not valid:
            with conn.cursor() as cur: cur.execute("INSERT INTO stream.order_dlq(payload,reason) VALUES(%s,%s)",(json.dumps(payload),reason))
            dlq.produce(s.kafka_dlq_topic,value=json.dumps({"payload":payload,"reason":reason})); dlq_count+=1
            if pending>=1000: conn.commit(); consumer.commit(message=last_msg,asynchronous=False); pending=0
            continue
        with conn.cursor() as cur:
            cur.execute("SELECT status_rank FROM stream.order_current WHERE order_id=%s",(payload["order_id"],)); current=cur.fetchone()
            is_ooo=bool(current and payload["status_rank"]<current[0]); out_of_order+=is_ooo
            cur.execute("""INSERT INTO stream.order_events(event_id,order_id,status,status_rank,event_ts,produced_at,out_of_order)
              VALUES(%(event_id)s,%(order_id)s,%(status)s,%(status_rank)s,%(event_ts)s,%(produced_at)s,%(ooo)s)
              ON CONFLICT(event_id) DO NOTHING RETURNING event_id""",{**payload,"ooo":is_ooo})
            inserted=cur.fetchone() is not None; new+=inserted; duplicate_count+=not inserted
            if inserted:
                cur.execute("""INSERT INTO stream.order_current(order_id,status,status_rank,event_ts,event_id)
                 VALUES(%(order_id)s,%(status)s,%(status_rank)s,%(event_ts)s,%(event_id)s)
                 ON CONFLICT(order_id) DO UPDATE SET status=EXCLUDED.status,status_rank=EXCLUDED.status_rank,event_ts=EXCLUDED.event_ts,event_id=EXCLUDED.event_id
                 WHERE EXCLUDED.status_rank>=stream.order_current.status_rank""",payload)
        if pending>=1000: conn.commit(); consumer.commit(message=last_msg,asynchronous=False); pending=0
      if pending and last_msg is not None: conn.commit(); consumer.commit(message=last_msg,asynchronous=False)
    consumer.close(); dlq.flush(30)
    with psycopg.connect(s.pg_dsn) as conn:
      with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM stream.order_events"); stored=cur.fetchone()[0]
        cur.execute("""SELECT count(*) FROM raw.orders o LEFT JOIN stream.order_current c USING(order_id)
                       WHERE c.order_id IS NULL OR c.status<>o.order_status"""); mismatch=cur.fetchone()[0]
        cur.execute("SELECT percentile_cont(.5) WITHIN GROUP(ORDER BY extract(epoch from(consumed_at-produced_at))),percentile_cont(.95) WITHIN GROUP(ORDER BY extract(epoch from(consumed_at-produced_at))) FROM stream.order_events"); p50,p95=cur.fetchone()
    producer_stats={"unique":len(events),"duplicates":duplicates,"late":late,"corrupt":corrupt}
    consumer_stats={"consumed":consumed,"new":new,"duplicates_ignored":duplicate_count,"out_of_order":out_of_order,"dlq":dlq_count,"stored_total":stored,"status_mismatch":mismatch,"freshness_p50_seconds":float(p50 or 0),"freshness_p95_seconds":float(p95 or 0)}
    data={"stage":"stream","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"producer":producer_stats,"consumer":consumer_stats}
    write_report("stream_report",data,"# Streaming replay\n\n## Producer\n\n"+markdown_table(["metric","count"],[[k,v] for k,v in producer_stats.items()])+"\n\n## Consumer\n\n"+markdown_table(["metric","count"],[[k,v] for k,v in consumer_stats.items()]))
    return data
