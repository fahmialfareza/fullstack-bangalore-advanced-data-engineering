# Business marts

| table | rows |
|---|---|
| monthly_sales | 11746 |
| delivery_performance | 565 |
| seller_scorecard | 3095 |
| customer_rfm | 96096 |
| order_reconciliation | 99441 |
| stream_freshness | 2 |

## Q1 — highest complete-month revenue

| month_key   |   revenue |
|:------------|----------:|
| 2017-11-01  |    995029 |
| 2018-04-01  |    990554 |
| 2018-05-01  |    985300 |
| 2018-03-01  |    970472 |
| 2018-01-01  |    934589 |

## Q2 — states with highest late rate

| customer_state   |   late |   delivered |   late_rate |
|:-----------------|-------:|------------:|------------:|
| AL               |     85 |         397 |    0.214106 |
| MA               |    125 |         720 |    0.173611 |
| SE               |     51 |         336 |    0.151786 |
| PI               |     66 |         476 |    0.138655 |
| CE               |    176 |        1281 |    0.137393 |

## Q3 — seller action list

| seller_id                        |   orders |   late_rate |   avg_review_score |
|:---------------------------------|---------:|------------:|-------------------:|
| 4342d4b2ba6b161468c63a7e7cfce593 |       20 |      0.5    |               1.26 |
| 2709af9587499e95e803a6498a5a56e9 |       26 |      0.5    |               2.57 |
| 54965bbe3e4f07ae045b90b0b8541f52 |       78 |      0.321  |               2.94 |
| 821fb029fc6e495ca4f08a35d51e53a5 |       28 |      0.32   |               3.43 |
| ede0c03645598cdfc63ca8237acbe73d |       46 |      0.3191 |               3.62 |

## Q4 — leading RFM segments

|   rfm_segment |   customers |    monetary |
|--------------:|------------:|------------:|
|           215 |        3510 | 1.45477e+06 |
|           415 |        3543 | 1.44754e+06 |
|           115 |        3540 | 1.42811e+06 |
|           515 |        3479 | 1.42057e+06 |
|           315 |        3391 | 1.24956e+06 |

## Reconciliation

| reason       |   orders |   total_abs_difference |
|:-------------|---------:|-----------------------:|
| matched      |    98362 |                   2.73 |
| no_items     |      775 |              162592    |
| installments |      266 |                3172.87 |
| unexplained  |       30 |                  78.87 |
| voucher      |        7 |                  17.48 |
| no_payment   |        1 |                 143.46 |
