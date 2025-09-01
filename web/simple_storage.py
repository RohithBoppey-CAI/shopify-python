import json
from pathlib import Path
from json.decoder import JSONDecodeError

# Build a path to 'session_storage.json' located in the SAME directory as this script.
STORAGE_FILE = Path(__file__).parent / "session_storage.json"

def save_token(shop: str, token: str):
    """Saves a token for a given shop to the JSON file."""
    data = {}
    if STORAGE_FILE.exists():
        try:
            # Try to load existing data
            with open(STORAGE_FILE, "r") as f:
                data = json.load(f)
        except JSONDecodeError:
            # If the file is empty or corrupt, start with an empty dict
            pass 

    # Add or update the token for the shop
    data[shop] = token

    # Write the updated data back to the file
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    print(f"[STORAGE] Saved token for {shop}")

def get_token(shop: str) -> str | None:
    """Retrieves a token for a given shop from the JSON file."""
    if not STORAGE_FILE.exists():
        return None

    try:
        with open(STORAGE_FILE, "r") as f:
            data = json.load(f)
            # Return the token if the shop exists, otherwise return None
            return data.get(shop)
    except JSONDecodeError:
        # If the file is empty or corrupt, there's no token to get
        return None