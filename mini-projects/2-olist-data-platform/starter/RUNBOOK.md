# Runbook — Olist Data Platform

## Start from zero

Follow the eight commands in `README.md`. If ports are occupied, edit only `.env`. `pipeline.py all` runs check → profile → bronze → silver → load → stream → model → marts → dashboard → report.

## Layer checks

| Layer | Check | Expected |
|---|---|---|
| source | `.venv/bin/python pipeline.py check` | nine OK rows |
| bronze | list `s3://bronze/olist/` with the configured MinIO endpoint | versions and manifests |
| silver | inspect `outputs/dq_report.md` | no FAIL |
| raw | query `select count(*) from raw.orders` | 99,441 |
| stream | configured Kafka UI | event and DLQ topics |
| DW | `.venv/bin/pytest -q tests/test_dw.py` | passed |
| mart | inspect `outputs/marts_report.md` | six marts and Q1–Q4 |

## Symptom → cheapest check → recovery

| Symptom | Check first | Recovery |
|---|---|---|
| port in use | `lsof -nP -iTCP:<port> -sTCP:LISTEN` | choose free `.env` port |
| `NoBrokersAvailable` | `lsof -nP -iTCP:39092 -sTCP:LISTEN` | run `pipeline.py up`; verify `.env` host port |
| authentication failed | compare `.env` with the local PostgreSQL settings | rebuild project-local runtime if credentials changed |
| MinIO refused | `lsof -nP -iTCP:19000 -sTCP:LISTEN` | run `pipeline.py up`; bronze is rerunnable |
| silver FAIL | first hard rule in DQ report | restore source from bronze |
| raw count doubled | load report | rerun transactional load |
| status mismatch | query event ranks | rerun consumer; IDs deduplicate |
| DLQ grows | group database DLQ reasons | repair producer schema |
| FK creation fails | DW orphan checks | repair unknown mapping and rebuild |
| Kafka UI unavailable | `docker compose -f docker-compose.kafka-ui.yml ps` | start the optional UI compose file |

`pipeline.py down` stops the three local processes and retains `data/local/`. `pipeline.py down -v` also deletes only that ignored project-local runtime directory; source CSV, silver cache, and reports remain. Rebuild with `up` and `all`. This workflow does not use Docker.

On macOS, local MinIO data is stored in a 10 GB sparse APFS image under `data/local/`. The image grows only with actual object data and prevents MinIO's host-wide 99%-usage guard from rejecting small development uploads. Shutdown detaches it; the next `up` mounts it again.
