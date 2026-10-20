#!/usr/bin/env python3
"""Single command entry point for the Olist data platform."""
from __future__ import annotations
import argparse, shutil, socket, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SERVICES=["postgres","kafka","minio","kafka-ui"]
def read_env():
    env={}; p=ROOT/".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k,v=line.split("=",1); env[k.strip()]=v.strip()
    return env
def compose(*args): return subprocess.run(["docker","compose",*args],cwd=ROOT,check=True)
def port_free(port):
    with socket.socket() as sock: return sock.connect_ex(("127.0.0.1",port))!=0
def cmd_init(_):
    if not (ROOT/".env").exists(): shutil.copy(ROOT/".env.example",ROOT/".env"); print("created .env")
    e=read_env()
    for label,key,default in [("postgres","POSTGRES_PORT",5432),("kafka","KAFKA_HOST_PORT",29092),("kafka-ui","KAFKA_UI_PORT",8080),("minio","MINIO_API_PORT",9000)]:
        port=int(e.get(key,default)); print(f"{label:10} {port}: {'available' if port_free(port) else 'in use'}")
    for d in ("data/raw","data/silver","data/quarantine","outputs","notebooks"): (ROOT/d).mkdir(parents=True,exist_ok=True)
def cmd_up(a):
    from olist_platform.local_services import up_local
    up_local()
def cmd_down(a):
    from olist_platform.local_services import down_local
    down_local(a.volumes)
def cmd_check(_):
    from olist_platform.batch import check; check()
def cmd_profile(_):
    from olist_platform.batch import profile; profile()
def cmd_bronze(_):
    from olist_platform.batch import bronze; bronze()
def cmd_silver(_):
    from olist_platform.batch import silver; silver()
def cmd_load(_):
    from olist_platform.batch import load; load()
def cmd_stream(a):
    from olist_platform.streaming import stream; stream(a.limit)
def cmd_model(_):
    from olist_platform.warehouse import model; model()
def cmd_marts(_):
    from olist_platform.warehouse import marts; marts()
def cmd_report(_):
    from olist_platform.evidence import report; print(report())
def cmd_dashboard(_):
    from olist_platform.dashboard import build_dashboard
    for path in build_dashboard(): print(path)
def cmd_inject(_):
    from olist_platform.failures import run_failure_tests; run_failure_tests()
def cmd_all(a):
    for fn in (cmd_check,cmd_profile,cmd_bronze,cmd_silver,cmd_load): fn(a)
    cmd_stream(a); cmd_model(a); cmd_marts(a); cmd_dashboard(a); cmd_report(a)
p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest="command",required=True)
q=sub.add_parser("init"); q.set_defaults(func=cmd_init)
q=sub.add_parser("up"); q.add_argument("--build",action="store_true"); q.add_argument("--jupyter",action="store_true"); q.set_defaults(func=cmd_up)
q=sub.add_parser("down"); q.add_argument("-v","--volumes",action="store_true"); q.set_defaults(func=cmd_down)
for name,fn in [("check",cmd_check),("profile",cmd_profile),("bronze",cmd_bronze),("silver",cmd_silver),("load",cmd_load),("model",cmd_model),("marts",cmd_marts),("dashboard",cmd_dashboard),("inject",cmd_inject),("report",cmd_report)]:
    q=sub.add_parser(name); q.set_defaults(func=fn)
for name,fn in [("stream",cmd_stream),("all",cmd_all)]:
    q=sub.add_parser(name); q.add_argument("--limit",type=int); q.set_defaults(func=fn)
if __name__=="__main__":
    args=p.parse_args(); args.func(args)
