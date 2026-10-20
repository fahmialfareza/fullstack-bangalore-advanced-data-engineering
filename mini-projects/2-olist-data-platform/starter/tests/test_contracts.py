import pandas as pd
from olist_platform.batch import _convert
from olist_platform.contracts import CONTRACTS
from olist_platform.streaming import event_id, make_events, validate
def test_nine_contracts_have_explicit_types():
    assert len(CONTRACTS)==9
    for contract in CONTRACTS.values(): assert set(contract.types)==set(contract.columns)
def test_zip_codes_keep_leading_zero():
    df=pd.DataFrame({c:["01003" if c=="customer_zip_code_prefix" else "x"] for c in CONTRACTS["customers"].columns})
    assert _convert(df,"customers").iloc[0].customer_zip_code_prefix=="01003"
def test_deterministic_event_id_and_validation():
    assert event_id("a","created")==event_id("a","created")
    assert validate({})[0] is False
def test_event_replay_reaches_final_status():
    ts=pd.Timestamp("2018-01-01")
    row={"order_id":"o","order_status":"delivered","order_purchase_timestamp":ts,"order_approved_at":ts,"order_delivered_carrier_date":ts,"order_delivered_customer_date":ts}
    events=make_events(row); assert events[-1]["status"]=="delivered"; assert len({e["event_id"] for e in events})==len(events)
