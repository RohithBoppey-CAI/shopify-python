import requests
from .shopify_auth_service import get_shop_access_token
from models.shopify_client import ShopifyAPIClient
from core.config import settings


def sync_reco_configurations(shop: str) -> dict:
    """
    Fetches configurations, builds full public URLs, and upserts them as metaobjects.
    """
    print(f"[DEBUG] Starting configuration sync for shop: {shop}")

    access_token = get_shop_access_token(shop)
    if not access_token:
        raise Exception(f"Could not find access token for shop {shop}")

    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)
    definition_id = client.ensure_metaobject_definition()

    # Call your internal API to get the reco configurations with relative paths
    external_api_url = "http://localhost:8001/api/reco-config"
    response = requests.post(external_api_url)
    response.raise_for_status()
    reco_data = response.json()

    product_recos = reco_data.get("product_recos", [])
    stats = {"created": 0, "updated": 0, "failed": 0}

    # Get the public base URL of this Shopify App (your ngrok URL) from settings
    public_app_url = settings.APP_URL

    for reco in product_recos:
        relative_path = reco.get("endpoint")

        # THIS IS THE FIX: Convert the relative path to a full, absolute URL
        if relative_path and relative_path.startswith("/"):
            # Combine the public ngrok URL with the relative path
            full_public_url = f"{public_app_url.rstrip('/')}{relative_path}"
            print(
                f"[SYNC] Converting relative path '{relative_path}' to absolute URL '{full_public_url}'"
            )
            # Overwrite the endpoint in the dictionary with the full URL
            reco["endpoint"] = full_public_url

        # Now, upsert the metaobject with the corrected, full URL
        status = client.upsert_metaobject(definition_id, reco)
        if status in ["created", "updated"]:
            stats[status] += 1
        else:
            stats["failed"] += 1

    print(
        f"[DEBUG] Sync complete for {shop}. Created: {stats['created']}, Updated: {stats['updated']}"
    )
    return stats
