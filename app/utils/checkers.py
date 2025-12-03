from dateutil.parser import parse


def is_valid_date(date):
    try:
        parsed_date = parse(date)
        return parsed_date
    except Exception:
        return None
