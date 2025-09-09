from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.config import settings
from services.shopify_auth_service import (
    get_install_url,
    verify_hmac_signature,
    get_shop_access_token,
    save_or_update_token_in_db,
    exchange_code_for_token,
)
from dependencies.shopify import get_shopify_client
from services.shopify_product_service import trigger_initial_product_sync
from models import ShopifyAPIClient

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")


@router.get("/install")
async def install_app(request: Request):
    """Redirects the merchant to the Shopify authorization URL to install the app."""
    shop = request.query_params.get("shop")
    if not shop:
        return HTMLResponse("Missing 'shop' parameter.", status_code=400)
    install_url = get_install_url(shop)
    return RedirectResponse(url=install_url)


@router.get("/callback")
async def auth_callback(request: Request):
    """Handles the callback from Shopify after the merchant authorizes the app."""
    shop = request.query_params.get("shop")
    code = request.query_params.get("code")

    if not shop or not code:
        return HTMLResponse("Missing 'shop' or 'code' parameter.", status_code=400)

    access_token = exchange_code_for_token(shop=shop, code=code)

    if access_token:
        save_or_update_token_in_db(shop=shop, access_token=access_token)
        client = ShopifyAPIClient(shop_url=shop, access_token=access_token)
        trigger_initial_product_sync(client=client)

    final_admin_url = f"{settings.APP_URL}/admin?{request.url.query}"
    return RedirectResponse(url=final_admin_url)


@router.get("/scopes")
async def get_access_scopes(client: ShopifyAPIClient = Depends(get_shopify_client)):
    """Get the access scopes for the authenticated shop."""
    try:
        return client.get_access_scopes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
