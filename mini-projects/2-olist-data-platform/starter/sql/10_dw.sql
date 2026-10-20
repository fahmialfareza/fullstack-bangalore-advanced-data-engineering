DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;

CREATE TABLE dw.dim_date AS
SELECT d::date AS date_key,
       EXTRACT(year FROM d)::int AS year,
       EXTRACT(month FROM d)::int AS month,
       date_trunc('month', d)::date AS month_key,
       (d >= DATE '2017-01-01' AND d < DATE '2018-09-01') AS is_complete_month
FROM generate_series(DATE '2016-01-01', DATE '2018-12-31', INTERVAL '1 day') d;
ALTER TABLE dw.dim_date ADD PRIMARY KEY (date_key);

CREATE TABLE dw.dim_geo AS
SELECT geolocation_zip_code_prefix AS zip_code,
       avg(geolocation_lat)::numeric(10,6) AS latitude,
       avg(geolocation_lng)::numeric(10,6) AS longitude,
       mode() WITHIN GROUP (ORDER BY geolocation_city) AS city,
       mode() WITHIN GROUP (ORDER BY geolocation_state) AS state
FROM raw.geolocation
GROUP BY geolocation_zip_code_prefix;
INSERT INTO dw.dim_geo VALUES ('UNKNOWN', NULL, NULL, 'unknown', 'NA');
ALTER TABLE dw.dim_geo ADD PRIMARY KEY (zip_code);

CREATE TABLE dw.dim_customer AS
WITH ranked AS (
  SELECT c.*, o.order_purchase_timestamp,
         row_number() OVER (PARTITION BY customer_unique_id ORDER BY o.order_purchase_timestamp DESC, customer_id DESC) rn
  FROM raw.customers c JOIN raw.orders o USING (customer_id)
)
SELECT customer_unique_id, customer_zip_code_prefix,
       customer_city, customer_state,
       CASE WHEN g.zip_code IS NULL THEN 'UNKNOWN' ELSE customer_zip_code_prefix END AS geo_key
FROM ranked r LEFT JOIN dw.dim_geo g ON g.zip_code=r.customer_zip_code_prefix WHERE rn=1;
ALTER TABLE dw.dim_customer ADD PRIMARY KEY (customer_unique_id);
ALTER TABLE dw.dim_customer ADD FOREIGN KEY (geo_key) REFERENCES dw.dim_geo(zip_code);

CREATE TABLE dw.dim_seller AS
SELECT s.*, CASE WHEN g.zip_code IS NULL THEN 'UNKNOWN' ELSE seller_zip_code_prefix END AS geo_key
FROM raw.sellers s LEFT JOIN dw.dim_geo g ON g.zip_code=s.seller_zip_code_prefix;
ALTER TABLE dw.dim_seller ADD PRIMARY KEY (seller_id);
ALTER TABLE dw.dim_seller ADD FOREIGN KEY (geo_key) REFERENCES dw.dim_geo(zip_code);

CREATE TABLE dw.dim_product AS
SELECT p.product_id,
       COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_name,
       p.product_name_lenght AS product_name_length,
       p.product_description_lenght AS product_description_length,
       p.product_photos_qty, p.product_weight_g, p.product_length_cm, p.product_height_cm, p.product_width_cm
FROM raw.products p LEFT JOIN raw.category_translation t USING (product_category_name);
ALTER TABLE dw.dim_product ADD PRIMARY KEY (product_id);

CREATE TABLE dw.fact_order AS
SELECT o.order_id, c.customer_unique_id, o.order_status,
       o.order_purchase_timestamp, o.order_approved_at, o.order_delivered_carrier_date,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       o.order_purchase_timestamp::date AS purchase_date_key,
       NOT EXISTS (SELECT 1 FROM raw.order_items i WHERE i.order_id=o.order_id) AS has_no_items,
       NOT EXISTS (SELECT 1 FROM raw.order_payments p WHERE p.order_id=o.order_id) AS has_no_payment,
       CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL
            ELSE o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date END AS is_late
FROM raw.orders o JOIN raw.customers c USING (customer_id);
ALTER TABLE dw.fact_order ADD PRIMARY KEY (order_id);
ALTER TABLE dw.fact_order ADD FOREIGN KEY (customer_unique_id) REFERENCES dw.dim_customer(customer_unique_id);
ALTER TABLE dw.fact_order ADD FOREIGN KEY (purchase_date_key) REFERENCES dw.dim_date(date_key);

CREATE TABLE dw.fact_order_item AS
SELECT i.*, o.order_purchase_timestamp::date AS purchase_date_key
FROM raw.order_items i JOIN raw.orders o USING (order_id);
ALTER TABLE dw.fact_order_item ADD PRIMARY KEY (order_id, order_item_id);
ALTER TABLE dw.fact_order_item ADD FOREIGN KEY (order_id) REFERENCES dw.fact_order(order_id);
ALTER TABLE dw.fact_order_item ADD FOREIGN KEY (product_id) REFERENCES dw.dim_product(product_id);
ALTER TABLE dw.fact_order_item ADD FOREIGN KEY (seller_id) REFERENCES dw.dim_seller(seller_id);
ALTER TABLE dw.fact_order_item ADD FOREIGN KEY (purchase_date_key) REFERENCES dw.dim_date(date_key);

CREATE TABLE dw.fact_payment AS SELECT * FROM raw.order_payments;
ALTER TABLE dw.fact_payment ADD PRIMARY KEY (order_id, payment_sequential);
ALTER TABLE dw.fact_payment ADD FOREIGN KEY (order_id) REFERENCES dw.fact_order(order_id);

CREATE TABLE dw.fact_review AS
WITH ranked AS (
 SELECT r.*, count(*) OVER (PARTITION BY order_id) AS review_count,
        row_number() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC NULLS LAST, review_creation_date DESC, review_id DESC) rn
 FROM raw.order_reviews r
)
SELECT review_id, order_id, review_score, review_comment_title, review_comment_message,
       review_creation_date, review_answer_timestamp, review_count
FROM ranked WHERE rn=1;
ALTER TABLE dw.fact_review ADD PRIMARY KEY (order_id);
ALTER TABLE dw.fact_review ADD FOREIGN KEY (order_id) REFERENCES dw.fact_order(order_id);
