"""Core Python functions used in the initial data review."""

def clean_name(name):
    """Return a trimmed, title-cased name."""
    raise NotImplementedError("clean_name has not been implemented")

def safe_city(user):
    """Return city when present; otherwise return 'Unknown'."""
    raise NotImplementedError("safe_city has not been implemented")

def classify_quantity(value):
    """Return 'positive-int', 'numeric-string', or 'invalid'."""
    raise NotImplementedError("classify_quantity has not been implemented")

def numbered_names(names):
    """Return names paired with sequence numbers beginning at one."""
    raise NotImplementedError("numbered_names has not been implemented")

def parse_quantity(value):
    """Return a positive integer; return None when conversion is invalid."""
    raise NotImplementedError("parse_quantity has not been implemented")
