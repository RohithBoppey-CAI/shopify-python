import json
from datetime import datetime
from typing import Union


def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_to_json(
    data_dict: Union[dict, list],
    filename: str = f"{get_current_datetime()}.json",
    base_dir: str = "./",
):
    with open(f"{base_dir}/{filename}", "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)
