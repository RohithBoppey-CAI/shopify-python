import requests
import json


def read_jsonl_from_url(url):
    all_objects = []
    try:
        response = requests.get(url)
        response.raise_for_status()

        for line in response.text.splitlines():
            try:
                obj = json.loads(line)
                all_objects.append(obj)
            except json.JSONDecodeError as err:
                print("Invalid JSON:", err)

        return all_objects

    except Exception as e:
        print(f"Connection error: {e}")
        return []


def return_dummy_handlers():
    x = [
        "proteus-fitness-jackshirt",
        "chaz-kangeroo-hoodie",
        "teton-pullover-hoodie",
        "bruno-complete-hoodie",
        "frankie-sweatshirt",
        "grayson-crewneck-sweatshirt",
        "mach-street-sweatshirt",
        "hyperion-elements-jacket",
        "beaumont-summit-kit",
        "jupiter-all-weather-trainer",
    ]
    return {"product_handles": x}
