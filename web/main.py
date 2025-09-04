from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
from datetime import timezone
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
from models import ShopifyAPIClient
import httpx
from fastapi.middleware.cors import CORSMiddleware
from utils.commons.api_utils import return_dummy_handlers

app = FastAPI(title="Couture Search Shopify App")


class SyncRequest(BaseModel):
    shop: str


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


origins = [
    "https://dummycouture.myshopify.com",
    "https://admin.shopify.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


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


@app.get("/api/reco/{reco_path:path}")
async def proxy_reco_request(reco_path: str, product_id: int):
    """
    This endpoint acts as a proxy to the internal recommendation service.
    """
    print("\n--- [PROXY LOG] ---")
    print("[PROXY] Received request from theme for path: /{reco_path}")

    # The internal URL of your other service
    internal_api_url = f"{settings.PROXY_SERVER_URL}/{reco_path}"
    if product_id:
        internal_api_url += f"?product_id={product_id}"
    print(f"[PROXY] Forwarding request to internal API: {internal_api_url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(internal_api_url)
            print(f"[PROXY] Received status {response.status_code} from internal API.")
            response.raise_for_status()
            print("[PROXY] Success! Forwarding response back to the theme.")
            print("--- [PROXY LOG END] ---\n")
            # return response.json()
            return return_dummy_handlers()
        except httpx.RequestError as exc:
            print(f"[ERROR] Proxy request to {internal_api_url} failed: {exc}")
            raise HTTPException(
                status_code=502,
                detail="Error connecting to the recommendation service.",
            )


@app.post("/sync-reco-config")
async def sync_config(sync_request: SyncRequest):
    """Handles the AJAX request and logs the sync result."""
    shop = sync_request.shop
    access_token = get_shop_access_token(shop)
    if not access_token:
        return {"error": f"Could not find access token for shop {shop}"}, 400

    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

    try:
        result = sync_reco_configurations(shop, client)  # Pass the client in
        message = f"Sync successful! {result['created']} created, {result['updated']} updated."

        # Log the successful result
        client.update_sync_history(
            key="reco_config_sync", status="success", message=message
        )

        return {"message": message}

    except Exception as e:
        error_message = f"Sync failed: {str(e)}"

        # Log the error
        client.update_sync_history(
            key="reco_config_sync", status="error", message=error_message
        )

        return {"error": str(e)}, 500


@app.get("/get-sync-history")
async def get_reco_sync_history(shop: str):
    """
    Fetches the sync history log, which is stored in a shop metafield.
    This endpoint is called by the admin dashboard on page load.
    """
    try:
        # 1. Authenticate and create an API client for the specific shop
        access_token = get_shop_access_token(shop)
        if not access_token:
            raise Exception("Could not find access token for the shop.")

        client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

        # 2. Fetch the specific metafield where we store the history
        history_metafield = client.get_metafield(
            namespace="couture_app", key="reco_config_sync"
        )

        # 3. Handle cases where no history exists yet
        if not history_metafield or not history_metafield.get("value"):
            return {"history": []}

        # 4. The metafield's value is a JSON string; parse it into a Python list
        history = json.loads(history_metafield["value"])

        # 5. Return the list to the frontend
        return {"history": history}

    except Exception as e:
        # Return a clear error if anything goes wrong
        return {"error": f"Failed to retrieve sync history: {str(e)}"}, 500


@app.post("/api/products/sync")
async def trigger_product_sync(request: Request, background_tasks: BackgroundTasks):
    """API endpoint to manually trigger a full product catalogue sync."""
    data = await request.json()
    shop = data.get("shop")
    if not shop:
        return {"error": "Shop domain is required."}, 400

    access_token = get_shop_access_token(shop)
    if not access_token:
        return {"error": f"Could not find access token for shop {shop}"}, 400

    client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

    try:
        # 1. Log the "processing" state immediately
        client.update_sync_history(
            key="catalogue_sync_history",
            status="processing",
            message="Full catalogue sync initiated by user.",
        )

        # background_tasks.add_task(run_bulk_product_sync, shop, client)

        trigger_initial_product_sync(shop)

        return {"message": "Product catalogue sync completed successfully."}

    except Exception as e:
        error_message = f"Catalogue sync failed: {str(e)}"

        # 4. Log the "error" state if something goes wrong
        client.update_sync_history(
            key="catalogue_sync_history", status="error", message=error_message
        )
        return {"error": error_message}, 500


@app.get("/get-catalogue-sync-history")
async def get_catalogue_sync_history(shop: str):
    """Fetches the catalogue sync history from a shop metafield."""
    try:
        access_token = get_shop_access_token(shop)
        if not access_token:
            raise Exception("Could not find access token.")

        client = ShopifyAPIClient(shop_url=shop, access_token=access_token)

        # Note the new, specific key for this history log
        history_metafield = client.get_metafield(
            namespace="couture_app", key="catalogue_sync_history"
        )

        if not history_metafield or not history_metafield.get("value"):
            return {"history": []}

        history = json.loads(history_metafield["value"])
        return {"history": history}

    except Exception as e:
        return {"error": f"Failed to get history: {str(e)}"}, 500


@app.get("/api/sync/status")
async def get_sync_status(shop: str):
    """API endpoint to check the status of the latest bulk operation."""
    status = get_last_sync_status(shop=shop)
    return status
