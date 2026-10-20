#!/usr/bin/env python3
"""T6 worker: commit one Kafka event to PostgreSQL, then die before offset commit."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
from confluent_kafka import Consumer

from olist_platform.config import settings

topic, group = sys.argv[1:3]
s=settings()
consumer=Consumer({"bootstrap.servers":s.kafka_bootstrap,"group.id":group,"enable.auto.commit":False,"auto.offset.reset":"earliest","session.timeout.ms":6000,"heartbeat.interval.ms":1000})
consumer.subscribe([topic])
while True:
    msg=consumer.poll(10)
    if msg is None: continue
    if msg.error(): raise RuntimeError(msg.error())
    payload=json.loads(msg.value())
    with psycopg.connect(s.pg_dsn) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS stream.crash_probe(event_id text PRIMARY KEY, attempts int NOT NULL DEFAULT 1)")
        conn.execute("INSERT INTO stream.crash_probe(event_id) VALUES(%s) ON CONFLICT(event_id) DO UPDATE SET attempts=stream.crash_probe.attempts+1",(payload["event_id"],))
    os._exit(137)
