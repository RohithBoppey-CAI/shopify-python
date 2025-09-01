import requests
from .shopify_auth_service import get_shop_access_token
from models.shopify_client import ShopifyAPIClient
from core.config import settings

def sync_reco_configurations(shop: str):
    """
    Fetches the latest banner/carousel configurations from the external API
    and syncs them to the Shopify store as Metaobjects.
    """
    print(f"[DEBUG] Starting configuration sync for shop: {shop}")
    
    access_token = get_shop_access_token(shop)
    if not access_token:
        raise Exception(f"Could not find access token for shop: {shop}")
    
    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

    # This will create the definition if it doesn't exist, or just return the ID if it does.
    metaobject_definition_id = client.ensure_metaobject_definition()
    print(f"[DEBUG] Using Metaobject Definition ID: {metaobject_definition_id}")
    
    # In a real app, this URL would also come from the settings
    external_api_url = "http://host.docker.internal:8000/reco-config" # Placeholder
    print(f"[DEBUG] Calling external API at: {external_api_url}")
    response = requests.get(external_api_url) # In a real app, add headers if needed
    response.raise_for_status()
    config_data = response.json()
    print(f"[DEBUG] Received {len(config_data.get('product_recos', []))} reco configs from API.")

    created_count = 0
    updated_count = 0
    
    for reco in config_data.get("product_recos", []):
        result = client.upsert_metaobject(metaobject_definition_id, reco)
        if result == 'created':
            created_count += 1
        elif result == 'updated':
            updated_count += 1
            
    print(f"[DEBUG] Sync complete for {shop}. Created: {created_count}, Updated: {updated_count}")
    return {"created": created_count, "updated": updated_count}

