# Silver quality gate

Threshold: **2% hard-rule quarantine per table**. Above it, the table is not loaded.

| table | source | silver | quarantine | ratio | verdict |
|---|---|---|---|---|---|
| customers | 99441 | 99441 | 0 | 0.000% | PASS |
| geolocation | 1000163 | 988476 | 11687 | 1.169% | PASS+QUARANTINE |
| order_items | 112650 | 112650 | 0 | 0.000% | PASS |
| order_payments | 103886 | 103886 | 0 | 0.000% | PASS |
| order_reviews | 99224 | 99224 | 0 | 0.000% | PASS |
| orders | 99441 | 99441 | 0 | 0.000% | PASS |
| products | 32951 | 32951 | 0 | 0.000% | PASS |
| sellers | 3095 | 3095 | 0 | 0.000% | PASS |
| category_translation | 71 | 71 | 0 | 0.000% | PASS |

## Rules

| table | rule | type | violations | action |
|---|---|---|---|---|
| customers | customer_id_required | hard | 0 | quarantine |
| customers | natural_key_unique | hard | 0 | quarantine |
| customers | customer_zip_code_prefix_five_digits | hard | 0 | quarantine |
| geolocation | geolocation_zip_code_prefix_five_digits | hard | 0 | quarantine |
| geolocation | geolocation_lat_parseable | hard | 0 | quarantine |
| geolocation | geolocation_lng_parseable | hard | 0 | quarantine |
| geolocation | coordinates_inside_brazil | hard | 11687 | quarantine |
| order_items | order_id_required | hard | 0 | quarantine |
| order_items | order_item_id_required | hard | 0 | quarantine |
| order_items | natural_key_unique | hard | 0 | quarantine |
| order_items | order_item_id_parseable | hard | 0 | quarantine |
| order_items | shipping_limit_date_parseable | hard | 0 | quarantine |
| order_items | price_parseable | hard | 0 | quarantine |
| order_items | freight_value_parseable | hard | 0 | quarantine |
| order_payments | order_id_required | hard | 0 | quarantine |
| order_payments | payment_sequential_required | hard | 0 | quarantine |
| order_payments | natural_key_unique | hard | 0 | quarantine |
| order_payments | payment_sequential_parseable | hard | 0 | quarantine |
| order_payments | payment_installments_parseable | hard | 0 | quarantine |
| order_payments | payment_value_parseable | hard | 0 | quarantine |
| order_payments | zero_payment | soft | 9 | report |
| order_payments | negative_payment | soft | 0 | report |
| order_reviews | review_id_required | hard | 0 | quarantine |
| order_reviews | order_id_required | hard | 0 | quarantine |
| order_reviews | natural_key_unique | hard | 0 | quarantine |
| order_reviews | review_score_parseable | hard | 0 | quarantine |
| order_reviews | review_creation_date_parseable | hard | 0 | quarantine |
| order_reviews | review_answer_timestamp_parseable | hard | 0 | quarantine |
| order_reviews | score_outside_1_5 | soft | 0 | report |
| order_reviews | empty_comment | soft | 58247 | report |
| orders | order_id_required | hard | 0 | quarantine |
| orders | natural_key_unique | hard | 0 | quarantine |
| orders | order_purchase_timestamp_parseable | hard | 0 | quarantine |
| orders | order_approved_at_parseable | hard | 0 | quarantine |
| orders | order_delivered_carrier_date_parseable | hard | 0 | quarantine |
| orders | order_delivered_customer_date_parseable | hard | 0 | quarantine |
| orders | order_estimated_delivery_date_parseable | hard | 0 | quarantine |
| orders | missing_approval_timestamp | soft | 160 | report |
| orders | delivered_missing_delivery_timestamp | soft | 8 | report |
| orders | delivery_before_carrier | soft | 23 | report |
| orders | unusual_status | soft | 0 | report |
| products | product_id_required | hard | 0 | quarantine |
| products | natural_key_unique | hard | 0 | quarantine |
| products | product_name_lenght_parseable | hard | 0 | quarantine |
| products | product_description_lenght_parseable | hard | 0 | quarantine |
| products | product_photos_qty_parseable | hard | 0 | quarantine |
| products | product_weight_g_parseable | hard | 0 | quarantine |
| products | product_length_cm_parseable | hard | 0 | quarantine |
| products | product_height_cm_parseable | hard | 0 | quarantine |
| products | product_width_cm_parseable | hard | 0 | quarantine |
| products | missing_category | soft | 610 | report |
| sellers | seller_id_required | hard | 0 | quarantine |
| sellers | natural_key_unique | hard | 0 | quarantine |
| sellers | seller_zip_code_prefix_five_digits | hard | 0 | quarantine |
| category_translation | product_category_name_required | hard | 0 | quarantine |
| category_translation | natural_key_unique | hard | 0 | quarantine |
