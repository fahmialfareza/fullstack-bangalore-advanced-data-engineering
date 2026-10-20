DROP SCHEMA IF EXISTS mart CASCADE;
CREATE SCHEMA mart;

CREATE TABLE mart.monthly_sales AS
SELECT d.month_key, d.is_complete_month, p.category_name, c.customer_state,
       count(DISTINCT o.order_id) AS orders, sum(i.price)::numeric(14,2) AS revenue,
       sum(i.freight_value)::numeric(14,2) AS freight
FROM dw.fact_order_item i JOIN dw.fact_order o USING(order_id)
JOIN dw.dim_product p USING(product_id) JOIN dw.dim_customer c USING(customer_unique_id)
JOIN dw.dim_date d ON d.date_key=o.purchase_date_key
WHERE o.order_status IN ('delivered','shipped')
GROUP BY d.month_key,d.is_complete_month,p.category_name,c.customer_state;

CREATE TABLE mart.delivery_performance AS
SELECT d.month_key, c.customer_state,
 count(*) FILTER (WHERE o.is_late IS NOT NULL) AS delivered,
 count(*) FILTER (WHERE o.is_late) AS late,
 avg(o.is_late::int) FILTER (WHERE o.is_late IS NOT NULL)::numeric(8,4) AS late_rate,
 avg(EXTRACT(epoch FROM (o.order_delivered_customer_date-o.order_purchase_timestamp))/86400)::numeric(8,2) AS avg_delivery_days,
 avg(r.review_score)::numeric(5,2) AS avg_review_score
FROM dw.fact_order o JOIN dw.dim_customer c USING(customer_unique_id)
JOIN dw.dim_date d ON d.date_key=o.purchase_date_key LEFT JOIN dw.fact_review r USING(order_id)
GROUP BY d.month_key,c.customer_state;

CREATE TABLE mart.seller_scorecard AS
SELECT s.seller_id,s.seller_state,count(DISTINCT i.order_id) AS orders,
 sum(i.price)::numeric(14,2) AS revenue,
 avg(o.is_late::int) FILTER(WHERE o.is_late IS NOT NULL)::numeric(8,4) AS late_rate,
 avg(r.review_score)::numeric(5,2) AS avg_review_score,
 avg((o.order_status='canceled')::int)::numeric(8,4) AS cancel_rate,
 (count(DISTINCT i.order_id)>=20) AS comparable
FROM dw.fact_order_item i JOIN dw.dim_seller s USING(seller_id) JOIN dw.fact_order o USING(order_id)
LEFT JOIN dw.fact_review r USING(order_id) GROUP BY s.seller_id,s.seller_state;

CREATE TABLE mart.customer_rfm AS
WITH base AS (
 SELECT customer_unique_id, max(order_purchase_timestamp)::date last_order,
        count(*) FILTER(WHERE order_status IN ('delivered','shipped')) frequency,
        COALESCE(sum(total),0)::numeric(14,2) monetary
 FROM dw.fact_order o LEFT JOIN (SELECT order_id,sum(price) total FROM dw.fact_order_item GROUP BY order_id) i USING(order_id)
 GROUP BY customer_unique_id
), scored AS (
 SELECT *, (DATE '2018-10-17'-last_order) recency_days,
  ntile(5) OVER(ORDER BY (DATE '2018-10-17'-last_order) DESC) r_score,
  CASE WHEN frequency=1 THEN 1 WHEN frequency=2 THEN 3 WHEN frequency=3 THEN 4 ELSE 5 END f_score,
  ntile(5) OVER(ORDER BY monetary) m_score FROM base
)
SELECT *, concat(r_score,f_score,m_score) AS rfm_segment FROM scored;

CREATE TABLE mart.order_reconciliation AS
WITH i AS (SELECT order_id,sum(price+freight_value) item_total FROM dw.fact_order_item GROUP BY order_id),
p AS (SELECT order_id,sum(payment_value) paid_total, bool_or(payment_type='voucher') has_voucher,
             max(payment_installments)>1 has_installments FROM dw.fact_payment GROUP BY order_id)
SELECT o.order_id,COALESCE(i.item_total,0)::numeric(14,2) item_total,COALESCE(p.paid_total,0)::numeric(14,2) paid_total,
 (COALESCE(p.paid_total,0)-COALESCE(i.item_total,0))::numeric(14,2) difference,
 CASE WHEN i.order_id IS NULL THEN 'no_items' WHEN p.order_id IS NULL THEN 'no_payment'
      WHEN abs(p.paid_total-i.item_total)<=.01 THEN 'matched'
      WHEN p.has_voucher THEN 'voucher' WHEN p.has_installments THEN 'installments' ELSE 'unexplained' END reason
FROM dw.fact_order o LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id);

CREATE TABLE mart.stream_freshness AS
SELECT date_trunc('minute',consumed_at) AS minute_ts,count(*) events,
 percentile_cont(.5) WITHIN GROUP(ORDER BY EXTRACT(epoch FROM(consumed_at-produced_at))) p50_seconds,
 percentile_cont(.95) WITHIN GROUP(ORDER BY EXTRACT(epoch FROM(consumed_at-produced_at))) p95_seconds
FROM stream.order_events GROUP BY 1;
