from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .config import settings


def _save(fig, name: str) -> None:
    target=settings().outputs_dir/"dashboard"; target.mkdir(parents=True,exist_ok=True)
    fig.tight_layout(); fig.savefig(target/name,dpi=150,bbox_inches="tight"); plt.close(fig)


def build_dashboard() -> list[Path]:
    out=settings().outputs_dir; made=[]
    sales=pd.read_parquet(out/"monthly_sales.parquet")
    monthly=sales[sales.is_complete_month].groupby("month_key").revenue.sum().sort_index()
    fig,ax=plt.subplots(figsize=(10,4)); monthly.plot(ax=ax,color="#2563eb",marker="o")
    ax.set(title="Olist revenue by complete month",xlabel="Month",ylabel="Revenue (BRL)"); _save(fig,"q1_revenue.png")

    delivery=pd.read_parquet(out/"delivery_performance.parquet").groupby("customer_state")[["late","delivered"]].sum()
    rates=(delivery.late/delivery.delivered).nlargest(10).sort_values()
    fig,ax=plt.subplots(figsize=(8,5)); rates.mul(100).plot.barh(ax=ax,color="#dc2626")
    ax.set(title="States with highest late-delivery rate",xlabel="Late deliveries (%)",ylabel="State"); _save(fig,"q2_delivery.png")

    seller=pd.read_parquet(out/"seller_scorecard.parquet"); seller=seller[seller.comparable].nlargest(10,"late_rate").sort_values("late_rate")
    fig,ax=plt.subplots(figsize=(8,5)); ax.barh(seller.seller_id.str[:8],seller.late_rate*100,color="#f97316")
    ax.set(title="Seller action list (minimum 20 orders)",xlabel="Late rate (%)",ylabel="Seller ID"); _save(fig,"q3_seller.png")

    rfm=pd.read_parquet(out/"customer_rfm.parquet").groupby("rfm_segment").agg(customers=("customer_unique_id","size"),monetary=("monetary","sum")).nlargest(10,"monetary").sort_values("monetary")
    fig,ax=plt.subplots(figsize=(8,5)); ax.barh(rfm.index.astype(str),rfm.monetary,color="#16a34a")
    ax.set(title="Highest-value RFM segments",xlabel="Revenue (BRL)",ylabel="RFM segment"); _save(fig,"q4_customers.png")

    fresh=pd.read_parquet(out/"stream_freshness.parquet")
    fig,ax=plt.subplots(figsize=(9,4))
    if len(fresh):
        ax.plot(fresh.minute_ts,fresh.p50_seconds,label="p50"); ax.plot(fresh.minute_ts,fresh.p95_seconds,label="p95"); ax.legend()
    ax.set(title="Kafka-to-PostgreSQL freshness",xlabel="Consumer minute",ylabel="Seconds"); _save(fig,"freshness.png")
    return sorted((out/"dashboard").glob("*.png"))
