def test_expected_grains(db):
    with db.cursor() as cur:
        for table,expected in [("dim_customer",96096),("fact_order",99441),("fact_order_item",112650)]:
            cur.execute(f"SELECT count(*) FROM dw.{table}"); assert cur.fetchone()[0]==expected
def test_dw_foreign_keys(db):
    with db.cursor() as cur:
        cur.execute("SELECT count(*) FROM dw.fact_order_item i LEFT JOIN dw.fact_order o USING(order_id) WHERE o.order_id IS NULL")
        assert cur.fetchone()[0]==0
