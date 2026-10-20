# Automated profile

| table | rows | exact duplicates | natural key unique | max null % |
|---|---|---|---|---|
| customers | 99441 | 0 | yes | 0.0 |
| geolocation | 1000163 | 261831 | n/a | 0.0 |
| order_items | 112650 | 0 | yes | 0.0 |
| order_payments | 103886 | 0 | yes | 0.0 |
| order_reviews | 99224 | 0 | yes | 88.342 |
| orders | 99441 | 0 | yes | 2.982 |
| products | 32951 | 0 | yes | 1.851 |
| sellers | 3095 | 0 | yes | 0.0 |
| category_translation | 71 | 0 | yes | 0.0 |

## Numbered findings

| # | table | finding | count A | count B | decision |
|---|---|---|---|---|---|
| 1 | customers | customer_id counts orders, customer_unique_id counts people | 99441 | 96096 | use unique id in dim_customer |
| 2 | customers | people with multiple order-scoped customer IDs | 2997 |  | handle in DW |
| 3 | orders | orders without items | 775 |  | retain with flag |
| 4 | orders | orders without payments | 1 |  | retain with flag |
| 5 | reviews | duplicate review_id rows | 1603 |  | deduplicate per order in DW |
| 6 | reviews | orders with multiple reviews | 547 |  | choose latest answer |
| 7 | geolocation | exact duplicate rows | 261831 |  | aggregate in DW |
| 8 | geolocation | coordinates outside Brazil bounds | 11687 |  | quarantine in silver |
| 9 | orders | delivered status missing delivery timestamp | 8 |  | soft rule; is_late null |
| 10 | orders | customer delivery earlier than carrier handoff | 23 |  | soft rule; retain and report |
| 11 | payments | zero-value payments | 9 |  | soft rule; retain |
| 12 | reconciliation | orders differing by more than BRL 0.01 | 1151 |  | classify in mart |
| 13 | reconciliation | orders differing by more than BRL 1.00 | 1022 |  | classify in mart |
