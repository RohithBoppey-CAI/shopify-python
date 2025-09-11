from models.shopify_client import ShopifyAPIClient
from utils.commons.api_utils import read_jsonl_from_url
from utils.commons.file_utils import save_to_json
import json


def trigger_initial_product_sync(client: ShopifyAPIClient) -> dict:
    """
    Starts a background bulk operation to fetch all products for a given store.
    """
    if client.is_bulk_operation_running():
        return {"status": "A sync operation is already in progress."}

    print("Triggering background catalogue!")
    result = client.fetch_all_products()

    return result


def trigger_order_history_sync(client: ShopifyAPIClient) -> dict:
    """
    Starts a background bulk operation to fetch all products for a given store.
    """

    if client.is_bulk_operation_running():
        return {"status": "A sync operation is already in progress."}

    print("Triggering order history download!")
    result = client.fetch_all_orders_information()
    return result


def get_last_sync_status(client: ShopifyAPIClient) -> dict:
    """
    Checks the status of the most recent bulk operation for a store.
    Only updates the metafield if the last record is in 'processing'.
    """

    status_data = client.get_bulk_operation_status()

    if not status_data or not status_data.get("status"):
        return {"message": "No active sync operation found."}

    final_status = status_data.get("status")

    # Determine which sync type this was based on the GraphQL query
    query = status_data.get("query", "")
    history_key = None
    filename_key = None

    if "products" in query:
        history_key = "catalogue_sync_history"
        filename_key = "products"
    elif "orders" in query:
        history_key = "order_sync_history"
        filename_key = "orders"

    if not history_key:
        print("No history key found")
        return status_data  # Not a sync we are tracking

    # --- NEW: fetch existing history ---
    existing_history = []
    existing_history_metafield = client.get_metafield(
        namespace="couture_app", key=history_key
    )
    if existing_history_metafield and existing_history_metafield.get("value"):
        existing_history = json.loads(existing_history_metafield["value"])

    last_record = existing_history[0] if existing_history else None

    # If last record is not 'processing', skip updating
    if not last_record or last_record.get("status") != "processing":
        print(
            f"Last sync for {history_key} is not in processing state. Skipping update."
        )
        return status_data

    # --- Only update if last record is processing ---
    if final_status == "COMPLETED":
        try:
            products = read_jsonl_from_url(status_data["url"])
            save_to_json(
                filename=f"downloads/{client.shop_url}_{filename_key}.jsonl", data_dict=products
            )
        except Exception as e:
            print(f"Cannot save information for {filename_key}: {e}")

        message = (
            f"Sync complete. {status_data.get('objectCount', 'All')} items indexed."
        )

        client.update_sync_history(
            key=history_key,
            status="success",
            message=message,
            update_latest_processing=True,
        )

    elif final_status in ["FAILED", "CANCELED", "EXPIRED"]:
        message = f"Sync {final_status.lower()}. Reason: {status_data.get('errorCode', 'Unknown')}"
        client.update_sync_history(
            key=history_key,
            status="error",
            message=message,
            update_latest_processing=True,
        )

    return status_data
