from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableContract:
    file: str
    columns: tuple[str, ...]
    types: dict[str, str]
    key: tuple[str, ...]
    expected_rows: int


def _types(columns: tuple[str, ...], *, timestamps=(), numerics=(), integers=(), zip_codes=()) -> dict[str, str]:
    result = {c: "text" for c in columns}
    result.update({c: "timestamp" for c in timestamps})
    result.update({c: "numeric" for c in numerics})
    result.update({c: "integer" for c in integers})
    result.update({c: "zip" for c in zip_codes})
    return result


def contract(file: str, columns: str, key: tuple[str, ...], rows: int, **typed) -> TableContract:
    cols = tuple(columns.split())
    return TableContract(file, cols, _types(cols, **typed), key, rows)


CONTRACTS = {
    "customers": contract("olist_customers_dataset.csv", "customer_id customer_unique_id customer_zip_code_prefix customer_city customer_state", ("customer_id",), 99_441, zip_codes=("customer_zip_code_prefix",)),
    "geolocation": contract("olist_geolocation_dataset.csv", "geolocation_zip_code_prefix geolocation_lat geolocation_lng geolocation_city geolocation_state", (), 1_000_163, zip_codes=("geolocation_zip_code_prefix",), numerics=("geolocation_lat", "geolocation_lng")),
    "order_items": contract("olist_order_items_dataset.csv", "order_id order_item_id product_id seller_id shipping_limit_date price freight_value", ("order_id", "order_item_id"), 112_650, timestamps=("shipping_limit_date",), numerics=("price", "freight_value"), integers=("order_item_id",)),
    "order_payments": contract("olist_order_payments_dataset.csv", "order_id payment_sequential payment_type payment_installments payment_value", ("order_id", "payment_sequential"), 103_886, numerics=("payment_value",), integers=("payment_sequential", "payment_installments")),
    "order_reviews": contract("olist_order_reviews_dataset.csv", "review_id order_id review_score review_comment_title review_comment_message review_creation_date review_answer_timestamp", ("review_id", "order_id"), 99_224, timestamps=("review_creation_date", "review_answer_timestamp"), integers=("review_score",)),
    "orders": contract("olist_orders_dataset.csv", "order_id customer_id order_status order_purchase_timestamp order_approved_at order_delivered_carrier_date order_delivered_customer_date order_estimated_delivery_date", ("order_id",), 99_441, timestamps=("order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date")),
    "products": contract("olist_products_dataset.csv", "product_id product_category_name product_name_lenght product_description_lenght product_photos_qty product_weight_g product_length_cm product_height_cm product_width_cm", ("product_id",), 32_951, numerics=("product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"), integers=("product_name_lenght", "product_description_lenght", "product_photos_qty")),
    "sellers": contract("olist_sellers_dataset.csv", "seller_id seller_zip_code_prefix seller_city seller_state", ("seller_id",), 3_095, zip_codes=("seller_zip_code_prefix",)),
    "category_translation": contract("product_category_name_translation.csv", "product_category_name product_category_name_english", ("product_category_name",), 71),
}


PG_TYPES = {"text": "text", "zip": "text", "timestamp": "timestamp", "numeric": "numeric", "integer": "integer"}
