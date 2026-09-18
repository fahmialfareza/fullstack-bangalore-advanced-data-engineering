"""Data cleaning functions for users, products, and transactions."""

def decision(entity, item_id, field, raw, action, clean, reason):
    """Create one standardized decision-log entry."""
    return {
        "entity": entity,
        "id": item_id,
        "field": field,
        "raw": raw,
        "action": action,
        "clean": clean,
        "reason": reason,
    }

def normalize_text(value):
    """Return trimmed text; return None for missing or empty input."""
    raise NotImplementedError("normalize_text has not been implemented")

def normalize_email(value):
    """Return a normalized email; return None when format is invalid."""
    raise NotImplementedError("normalize_email has not been implemented")

def parse_non_negative_float(value):
    """Return a float greater than or equal to zero; otherwise return None."""
    raise NotImplementedError("parse_non_negative_float has not been implemented")

def parse_positive_int(value):
    """Return a positive integer; reject booleans and decimals."""
    raise NotImplementedError("parse_positive_int has not been implemented")

def clean_users(rows):
    """Return (clean, rejected, decisions) for user records."""
    raise NotImplementedError("clean_users has not been implemented")

def clean_products(rows):
    """Return (clean, rejected, decisions) for product records."""
    raise NotImplementedError("clean_products has not been implemented")

def clean_transactions(rows):
    """Return (clean, rejected, decisions) for transaction records."""
    raise NotImplementedError("clean_transactions has not been implemented")
