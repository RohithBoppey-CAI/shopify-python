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
