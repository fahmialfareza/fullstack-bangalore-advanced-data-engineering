from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path

from .config import ROOT

RUNTIME=ROOT/"data/local"
LOGS=RUNTIME/"logs"
POSTGRES_BIN=Path("/Applications/Postgres.app/Contents/Versions/16/bin")
MINIO_IMAGE=RUNTIME/"minio.sparseimage"
MINIO_DATA=RUNTIME/"minio"


def _exe(name: str, fallback: Path | None = None) -> str:
    found=shutil.which(name)
    if found: return found
    if fallback and fallback.exists(): return str(fallback)
    raise RuntimeError(f"required local binary not found: {name}")


def _free(port: int) -> bool:
    with socket.socket() as sock: return sock.connect_ex(("127.0.0.1",port)) != 0


def _spawn(name: str, command: list[str], env: dict[str,str] | None=None) -> None:
    LOGS.mkdir(parents=True,exist_ok=True); pid_file=RUNTIME/f"{name}.pid"
    if pid_file.exists():
        try: os.kill(int(pid_file.read_text()),0); return
        except (OSError,ValueError): pid_file.unlink(missing_ok=True)
    log=(LOGS/f"{name}.log").open("ab")
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    pid_file.write_text(str(process.pid))


def _prepare_minio_storage() -> None:
    """Mount a sparse local volume so MinIO works when the host is over 99% full."""
    if os.path.ismount(MINIO_DATA): return
    if shutil.which("hdiutil"):
        if MINIO_DATA.exists() and any(MINIO_DATA.iterdir()):
            return  # Preserve an existing plain-directory deployment.
        MINIO_DATA.mkdir(parents=True,exist_ok=True)
        if not MINIO_IMAGE.exists():
            subprocess.run(["hdiutil","create","-size","10g","-type","SPARSE","-fs","APFS","-volname","OlistMinio",str(MINIO_IMAGE)],check=True,capture_output=True)
        subprocess.run(["hdiutil","attach","-nobrowse","-mountpoint",str(MINIO_DATA),str(MINIO_IMAGE)],check=True,capture_output=True)
    else:
        MINIO_DATA.mkdir(parents=True,exist_ok=True)


def init_local() -> None:
    RUNTIME.mkdir(parents=True,exist_ok=True)
    pgdata=RUNTIME/"postgres"
    if not (pgdata/"PG_VERSION").exists():
        subprocess.run([_exe("initdb",POSTGRES_BIN/"initdb"),"-D",str(pgdata),"-U","olist","--auth=trust"],check=True)
        # Keep transient WAL small on developer machines with limited disk space.
        with (pgdata/"postgresql.conf").open("a",encoding="utf-8") as config:
            config.write("\nmax_wal_size = '128MB'\nmin_wal_size = '32MB'\ncheckpoint_timeout = '2min'\n")
    kafka=RUNTIME/"kafka"; kafka.mkdir(exist_ok=True)
    config=RUNTIME/"kafka.properties"
    config.write_text(f"""process.roles=broker,controller
node.id=1
controller.quorum.bootstrap.servers=127.0.0.1:39093
listeners=PLAINTEXT://127.0.0.1:39092,CONTROLLER://127.0.0.1:39093
advertised.listeners=PLAINTEXT://127.0.0.1:39092
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
log.dirs={kafka}
log.retention.bytes=134217728
log.retention.check.interval.ms=30000
num.partitions=3
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
""",encoding="utf-8")
    if not (kafka/"meta.properties").exists():
        env={**os.environ,"KAFKA_JMX_OPTS":"","JMX_PORT":""}
        cluster=subprocess.run([_exe("kafka-storage"),"random-uuid"],capture_output=True,text=True,check=True,env=env).stdout.strip().splitlines()[-1]
        subprocess.run([_exe("kafka-storage"),"format","--standalone","-t",cluster,"-c",str(config)],check=True,env=env)


def up_local() -> None:
    init_local()
    _prepare_minio_storage()
    if _free(55432):
        _spawn("postgres",[_exe("postgres",POSTGRES_BIN/"postgres"),"-D",str(RUNTIME/"postgres"),"-p","55432","-h","127.0.0.1"])
    if _free(39092):
        env={**os.environ,"KAFKA_JMX_OPTS":"","JMX_PORT":"","KAFKA_HEAP_OPTS":"-Xms256m -Xmx512m"}
        _spawn("kafka",[_exe("kafka-server-start"),str(RUNTIME/"kafka.properties")],env)
    if _free(19000):
        env={**os.environ,"MINIO_ROOT_USER":"minio","MINIO_ROOT_PASSWORD":"minio_dev_only"}
        _spawn("minio",[_exe("minio"),"server",str(MINIO_DATA),"--address","127.0.0.1:19000"],env)
    deadline=time.time()+60
    while time.time()<deadline:
        if all(not _free(p) for p in (55432,39092,19000)): print("local services healthy: postgres:55432, kafka:39092, minio:19000"); return
        time.sleep(.5)
    raise RuntimeError(f"local service startup failed; inspect {LOGS}")


def down_local(remove_data: bool=False) -> None:
    pids: list[int] = []
    for name in ("minio","kafka","postgres"):
        pid_file=RUNTIME/f"{name}.pid"
        if pid_file.exists():
            try:
                pid=int(pid_file.read_text()); pids.append(pid)
                os.killpg(pid,signal.SIGTERM)
            except (ProcessLookupError,ValueError): pass
            pid_file.unlink(missing_ok=True)
    # Wait for service processes to release their files before deleting runtime data.
    deadline=time.time()+15
    while pids and time.time()<deadline:
        alive=[]
        for pid in pids:
            try: os.kill(pid,0); alive.append(pid)
            except ProcessLookupError: pass
        pids=alive
        if pids: time.sleep(.1)
    for pid in pids:
        try: os.killpg(pid,signal.SIGKILL)
        except ProcessLookupError: pass
    if os.path.ismount(MINIO_DATA):
        subprocess.run(["hdiutil","detach",str(MINIO_DATA),"-force"],check=False,capture_output=True)
    if remove_data:
        shutil.rmtree(RUNTIME,ignore_errors=True)


def stop_service(name: str) -> None:
    """Stop one project-local service and wait until its process exits."""
    pid_file=RUNTIME/f"{name}.pid"
    if not pid_file.exists(): return
    try:
        pid=int(pid_file.read_text()); os.killpg(pid,signal.SIGTERM)
        for _ in range(100):
            try: os.kill(pid,0)
            except ProcessLookupError: break
            time.sleep(.05)
    except (ProcessLookupError,ValueError): pass
    pid_file.unlink(missing_ok=True)
