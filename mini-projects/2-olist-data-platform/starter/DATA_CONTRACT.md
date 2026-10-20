# Data contract — Olist Data Platform

Source: Brazilian E-Commerce Public Dataset by Olist, validated by `scripts/check_dataset.py`. Timestamps are local Brazil time without a timezone, currency is BRL, and ZIP prefixes are five-character text.

| Table | Expected rows | Natural key | Target columns and types |
|---|---:|---|---|
| customers | 99,441 | `customer_id` | IDs/city/state text; ZIP text(5) |
| geolocation | 1,000,163 | repeated observations | ZIP text(5), lat/lng numeric, city/state text |
| order_items | 112,650 | (`order_id`, `order_item_id`) | IDs text, item integer, timestamp, price/freight numeric |
| order_payments | 103,886 | (`order_id`, `payment_sequential`) | IDs/type text, sequence/installments integer, value numeric |
| order_reviews | 99,224 | (`review_id`, `order_id`) | IDs/comments text, score integer, timestamps |
| orders | 99,441 | `order_id` | IDs/status text, all date-time fields timestamp |
| products | 32,951 | `product_id` | IDs/category text, counts integer, weight/dimensions numeric |
| sellers | 3,095 | `seller_id` | ID/city/state text, ZIP text(5) |
| category_translation | 71 | `product_category_name` | names text |

The column-level executable contract is `olist_platform/contracts.py`; profiling, conversion, DDL, and tests share it.

## Dirty-data findings and decisions

| # | Measured finding | Decision | Stage |
|---|---|---|---|
| 1 | 99,441 customer IDs vs 96,096 people | model unique ID | T4 |
| 2 | 2,997 people have multiple customer IDs | latest address SCD1 | T4 |
| 3 | 775 orders lack items | retain and flag | T4 |
| 4 | 1 order lacks payment | retain and flag | T4 |
| 5 | 1,603 review rows use duplicate review IDs | composite source key | T2/T4 |
| 6 | 547 orders have multiple reviews | latest answer + count | T4 |
| 7 | 261,831 exact geo duplicates | aggregate by ZIP | T4 |
| 8 | 11,687 coordinates outside bounds | quarantine | T2 |
| 9 | 8 delivered orders lack delivery time | retain; late null | T2/T4 |
| 10 | 23 deliveries precede carrier handoff | report and retain | T2 |
| 11 | 9 zero-value payments | report and retain | T2/T5 |
| 12 | 1,151 reconciliations differ over BRL 0.01 | classify | T5 |
| 13 | 1,022 differ over BRL 1.00 | classify and ask finance | T5 |

Hard rules quarantine malformed keys, duplicates, unparseable values, invalid ZIPs, and out-of-bounds coordinates. Soft rules report optional missing times, temporal anomalies, payment anomalies, unusual statuses, empty comments, and missing categories. More than 2% hard violations fails before load.

Customer grain is `customer_unique_id`; review grain is one row per order; geolocation grain is ZIP prefix. `is_late` is null without actual delivery. Complete months are January 2017 through August 2018.
