import pandas as pd
import pytest

from olist_platform.batch import _convert
from olist_platform.contracts import CONTRACTS
from olist_platform.streaming import STATUS_RANK, make_events, validate


def frame(name, **values):
    contract=CONTRACTS[name]
    return pd.DataFrame({column:[values.get(column,"")] for column in contract.columns})


def test_blank_numeric_and_timestamp_become_null():
    out=_convert(frame("order_items",order_id="o",order_item_id="1",product_id="p",seller_id="s"),"order_items")
    assert pd.isna(out.loc[0,"price"]) and pd.isna(out.loc[0,"shipping_limit_date"])


def test_numeric_and_integer_types_are_explicit():
    out=_convert(frame("order_payments",order_id="o",payment_sequential="1",payment_type="credit_card",payment_installments="3",payment_value="10.25"),"order_payments")
    assert str(out.payment_sequential.dtype)=="Int64" and out.loc[0,"payment_value"]==10.25


def test_invalid_timestamp_is_quarantine_candidate():
    source=frame("orders",order_id="o",customer_id="c",order_status="created",order_purchase_timestamp="not-a-date")
    out=_convert(source,"orders")
    assert source.order_purchase_timestamp.ne("").iloc[0] and pd.isna(out.order_purchase_timestamp.iloc[0])


@pytest.mark.parametrize("payload,reason",[
    ([],"payload_not_object"),
    ({},"missing_fields"),
    ({"event_id":"e","order_id":"o","status":"created","status_rank":10,"event_ts":"bad","produced_at":"2026-01-01T00:00:00+00:00"},"invalid_timestamp"),
    ({"event_id":"e","order_id":"o","status":"teleported","status_rank":10,"event_ts":"2020-01-01T00:00:00","produced_at":"2026-01-01T00:00:00+00:00"},"unknown_status"),
])
def test_malformed_stream_payloads(payload,reason):
    valid,actual=validate(payload)
    assert not valid and actual.startswith(reason)


@pytest.mark.parametrize("final",["created","approved","shipped","delivered","canceled","unavailable"])
def test_event_plan_always_contains_final_status(final):
    ts=pd.Timestamp("2018-01-01")
    row={"order_id":"o","order_status":final,"order_purchase_timestamp":ts,"order_approved_at":ts,
         "order_delivered_carrier_date":ts if STATUS_RANK.get(final,0)>=40 else None,
         "order_delivered_customer_date":ts if final=="delivered" else None}
    assert final in {event["status"] for event in make_events(row)}


def test_real_contract_has_required_rule_capacity():
    hard=sum(len(c.key)+1+sum(t in {"timestamp","numeric","integer","zip"} for t in c.types.values()) for c in CONTRACTS.values())
    assert hard>=10
