def clean_name(name):
    return name.strip().title()


def safe_city(user):
    return user.get("city", "Unknown")


def classify_quantity(value):
    if isinstance(value, bool):
        return "invalid"
    if isinstance(value, int) and value > 0:
        return "positive-int"
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return "numeric-string"
    return "invalid"


def numbered_names(names):
    return list(enumerate(names, start=1))


def parse_quantity(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
