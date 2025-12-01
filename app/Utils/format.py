from datetime import datetime


def format_time(timestamp: datetime):
    time = timestamp.strftime("%H:%M:%S")
    return time


def format_date(timestamp: datetime):
    date = timestamp.strftime("%D")
    return date
