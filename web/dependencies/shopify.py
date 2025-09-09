from fastapi import Depends, HTTPException, Request
from models import ShopifyAPIClient
from services.shopify_auth_service import get_shop_access_token, verify_hmac_signature


async def get_shopify_client(
    shop: str = Depends(verify_hmac_signature),
) -> ShopifyAPIClient:
    """Dependency that returns an authenticated ShopifyAPIClient instance with HMAC verification."""
    if not shop:
        raise HTTPException(status_code=403, detail="Could not verify Shopify request")

    access_token = get_shop_access_token(shop)
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token found for shop")

    return ShopifyAPIClient(shop_url=shop, access_token=access_token)


async def get_shopify_client_from_query(request: Request) -> ShopifyAPIClient:
    """Dependency that returns an authenticated ShopifyAPIClient instance from query parameters."""
    shop = request.query_params.get("shop")
    if not shop:
        raise HTTPException(status_code=400, detail="Missing 'shop' parameter")

    access_token = get_shop_access_token(shop)

    if not access_token:
        raise HTTPException(status_code=401, detail="No access token found for shop")

    return ShopifyAPIClient(shop_url=shop, access_token=access_token)
