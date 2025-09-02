import os
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.config import settings
from services.shopify_auth_service import get_install_url, verify_hmac_signature
from services.shopify_auth_service import (
    get_shop_access_token,
    save_or_update_token_in_db,
    exchange_code_for_token,
)
from services.shopify_product_service import (
    trigger_initial_product_sync,
    get_last_sync_status,
)
from services.shopify_config_service import sync_reco_configurations
from models.database import create_db_and_tables

app = FastAPI(title="Couture Search Shopify App")


class SyncRequest(BaseModel):
    shop: str


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    """Welcome endpoint for health checks."""
    return {"message": "Welcome to the Couture Search Shopify App"}


@app.get("/install")
async def install_app(request: Request):
    """Redirects the merchant to the Shopify authorization URL to install the app."""
    shop = request.query_params.get("shop")
    if not shop:
        return HTMLResponse("Missing 'shop' parameter.", status_code=400)
    install_url = get_install_url(shop)
    return RedirectResponse(url=install_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handles the callback from Shopify after the merchant authorizes the app."""
    shop = request.query_params.get("shop")
    code = request.query_params.get("code")

    if not shop or not code:
        return HTMLResponse("Missing 'shop' or 'code' parameter.", status_code=400)

    access_token = exchange_code_for_token(shop=shop, code=code)

    if access_token:
        save_or_update_token_in_db(shop=shop, access_token=access_token)
        trigger_initial_product_sync(shop=shop)

    final_admin_url = f"{settings.APP_URL}/admin?{request.url.query}"
    return RedirectResponse(url=final_admin_url)


@app.post("/api/products/sync")
async def trigger_product_sync(request: Request):
    """API endpoint to manually trigger a full product catalogue sync."""
    data = await request.json()
    shop = data.get("shop")
    result = trigger_initial_product_sync(shop=shop)
    return result


@app.get("/api/sync/status")
async def get_sync_status(shop: str):
    """API endpoint to check the status of the latest bulk operation."""
    status = get_last_sync_status(shop=shop)
    return status


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, shop: str = Depends(verify_hmac_signature)):
    """Serves the main admin dashboard UI for the app, protected by HMAC verification."""
    if not shop:
        return HTMLResponse(
            "Could not verify the request came from Shopify.", status_code=403
        )

    token_exists = get_shop_access_token(shop)
    if not token_exists:
        return RedirectResponse(url=f"/install?shop={shop}")

    host = request.query_params.get("host")
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "shop": shop,
            "host": host,
        },
    )


@app.post("/sync-reco-config")
async def sync_config(sync_request: SyncRequest):
    """Handles the AJAX request from the 'Sync Config' button in the admin dashboard."""
    shop = sync_request.shop
    try:
        result = sync_reco_configurations(shop)
        return {
            "message": f"Sync successful! {result['created']} created, {result['updated']} updated."
        }
    except Exception as e:
        return {"error": str(e)}, 500
