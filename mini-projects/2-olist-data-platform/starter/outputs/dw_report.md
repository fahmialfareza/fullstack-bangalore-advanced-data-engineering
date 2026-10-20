# Data warehouse

## Row counts

| table | rows |
|---|---|
| dim_date | 1096 |
| dim_geo | 18677 |
| dim_customer | 96096 |
| dim_product | 32951 |
| dim_seller | 3095 |
| fact_order | 99441 |
| fact_order_item | 112650 |
| fact_payment | 103886 |
| fact_review | 98673 |

## Integrity (all must be zero)

| check | violations |
|---|---|
| fact_order_orphan_customer | 0 |
| item_orphan_order | 0 |
| item_orphan_product | 0 |
| item_orphan_seller | 0 |
