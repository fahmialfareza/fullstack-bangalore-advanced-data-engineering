from __future__ import annotations

import json
import time

import pandas as pd
import psycopg

from .config import ROOT, settings
from .utils import markdown_table, now_iso, write_report
from .batch import _s3, ensure_buckets


def _run_sql(path):
    with psycopg.connect(settings().pg_dsn) as conn:
        with conn.cursor() as cur: cur.execute(path.read_text(encoding="utf-8"))


def _read_df(conn, query: str) -> pd.DataFrame:
    """Return a query as a DataFrame without relying on pandas' SQLAlchemy adapter."""
    with conn.cursor() as cur:
        cur.execute(query)
        columns=[column.name for column in cur.description]
        return pd.DataFrame(cur.fetchall(),columns=columns)


def model() -> dict:
    started=time.perf_counter(); _run_sql(ROOT/"sql/10_dw.sql")
    tables=["dim_date","dim_geo","dim_customer","dim_product","dim_seller","fact_order","fact_order_item","fact_payment","fact_review"]
    rows=[]; checks=[]
    with psycopg.connect(settings().pg_dsn) as conn:
      with conn.cursor() as cur:
        for table in tables: cur.execute(f"SELECT count(*) FROM dw.{table}"); rows.append([table,cur.fetchone()[0]])
        queries={"fact_order_orphan_customer":"SELECT count(*) FROM dw.fact_order f LEFT JOIN dw.dim_customer d USING(customer_unique_id) WHERE d.customer_unique_id IS NULL",
                 "item_orphan_order":"SELECT count(*) FROM dw.fact_order_item f LEFT JOIN dw.fact_order d USING(order_id) WHERE d.order_id IS NULL",
                 "item_orphan_product":"SELECT count(*) FROM dw.fact_order_item f LEFT JOIN dw.dim_product d USING(product_id) WHERE d.product_id IS NULL",
                 "item_orphan_seller":"SELECT count(*) FROM dw.fact_order_item f LEFT JOIN dw.dim_seller d USING(seller_id) WHERE d.seller_id IS NULL"}
        for name,q in queries.items(): cur.execute(q); checks.append([name,cur.fetchone()[0]])
    data={"stage":"model","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"tables":rows,"integrity":checks}
    write_report("dw_report",data,"# Data warehouse\n\n## Row counts\n\n"+markdown_table(["table","rows"],rows)+"\n\n## Integrity (all must be zero)\n\n"+markdown_table(["check","violations"],checks)); return data


def marts() -> dict:
    started=time.perf_counter(); _run_sql(ROOT/"sql/20_marts.sql"); ensure_buckets(); client=_s3()
    tables=["monthly_sales","delivery_performance","seller_scorecard","customer_rfm","order_reconciliation","stream_freshness"]
    rows=[]
    with psycopg.connect(settings().pg_dsn) as conn:
      for table in tables:
        df=_read_df(conn,f"SELECT * FROM mart.{table}"); rows.append([table,len(df)])
        path=settings().outputs_dir/f"{table}.parquet"; df.to_parquet(path,index=False); client.upload_file(str(path),"gold",f"olist/{table}/data.parquet")
      q1=_read_df(conn,"SELECT month_key,sum(revenue) revenue FROM mart.monthly_sales WHERE is_complete_month GROUP BY month_key ORDER BY revenue DESC LIMIT 5")
      q2=_read_df(conn,"SELECT customer_state,sum(late) late,sum(delivered) delivered,(sum(late)::numeric/nullif(sum(delivered),0)) late_rate FROM mart.delivery_performance GROUP BY customer_state ORDER BY late_rate DESC LIMIT 5")
      q3=_read_df(conn,"SELECT seller_id,orders,late_rate,avg_review_score FROM mart.seller_scorecard WHERE comparable ORDER BY late_rate DESC,avg_review_score LIMIT 5")
      q4=_read_df(conn,"SELECT rfm_segment,count(*) customers,sum(monetary) monetary FROM mart.customer_rfm GROUP BY rfm_segment ORDER BY monetary DESC LIMIT 5")
      rec=_read_df(conn,"SELECT reason,count(*) orders,sum(abs(difference)) total_abs_difference FROM mart.order_reconciliation GROUP BY reason ORDER BY orders DESC")
    answers={"q1":q1.to_dict("records"),"q2":q2.to_dict("records"),"q3":q3.to_dict("records"),"q4":q4.to_dict("records"),"reconciliation":rec.to_dict("records")}
    data={"stage":"marts","generated_at":now_iso(),"duration_seconds":round(time.perf_counter()-started,3),"tables":rows,"answers":answers}
    md="# Business marts\n\n"+markdown_table(["table","rows"],rows)
    for title,df in [("Q1 — highest complete-month revenue",q1),("Q2 — states with highest late rate",q2),("Q3 — seller action list",q3),("Q4 — leading RFM segments",q4),("Reconciliation",rec)]:
        md+=f"\n\n## {title}\n\n"+df.to_markdown(index=False)
    write_report("marts_report",data,md); return data
