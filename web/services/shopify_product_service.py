# services/shopify_product_service.py
import time
from models.shopify_client import ShopifyAPIClient
from utils.commons.api_utils import read_jsonl_from_url
from utils.commons.file_utils import save_to_json


def get_access_token_for_shop(shop: str) -> str:
    """
    Retrieves the access token for a given shop.
    In a real application, this would fetch from a secure database.
    """
    try:
        with open(f"{shop}_token.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise Exception(f"Access token for shop {shop} not found.")


def trigger_initial_product_sync(shop: str) -> dict:
    """
    Starts a background bulk operation to fetch all products for a given store.
    """
    access_token = get_access_token_for_shop(shop)
    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

    if client.is_bulk_operation_running():
        return {"status": "A sync operation is already in progress."}

    print(f"Triggering background catalogue download for the shop {shop}")
    result = client.fetch_all_products(wait=False)

    return result


def get_last_sync_status(shop: str) -> dict:
    """
    Checks the status of the most recent bulk operation for a store.
    """
    access_token = get_access_token_for_shop(shop)
    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)
    status = client.get_bulk_operation_status()

    # If the operation is complete, download and save the data
    if status.get("status") == "COMPLETED" and status.get("url"):
        products = read_jsonl_from_url(status["url"])
        save_to_json(filename=f"{shop}_products.jsonl", data_dict=products)
        # TODO: Update the status in your database to "Completed".

    client.update_sync_history(
        key="catalogue_sync_history",
        status="success",
        message="Sync complete",
        update_latest_processing=True,
    )

    return status
