from dateutil.parser import parse
from datetime import date


def is_valid_date(date):
    try:
        parsed_date = parse(date)
        return parsed_date.date()
    except Exception as e:
        return None
