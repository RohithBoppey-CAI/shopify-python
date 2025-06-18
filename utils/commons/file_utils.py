import json
from datetime import datetime


def get_current_datetime():
    current_dateTime = datetime.now()
    day = current_dateTime.day
    month = current_dateTime.month
    hour = current_dateTime.hour
    minute = current_dateTime.minute
    second = current_dateTime.second
    return f"{month}_{day}_{hour}_{minute}_{second}"


def save_to_json(data_dict: dict, filename: str = get_current_datetime()):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)
