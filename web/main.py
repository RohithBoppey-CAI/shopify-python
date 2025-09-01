import os
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.config import settings

from simple_storage import save_token, get_token

# Correctly import all necessary services
from services.shopify_auth_service import (
    get_install_url,
    exchange_code_for_token,
    verify_shopify_request,
    get_shop_access_token,
    save_or_update_token_in_db,
)
from services.shopify_product_service import (
    trigger_initial_product_sync,
    get_last_sync_status,
)
from services.shopify_config_service import sync_reco_configurations
from models.database import create_db_and_tables

app = FastAPI(
    title="Couture Search Shopify App",
    description="API for handling Shopify integration and providing recommendation services.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    """
    This function runs when the app starts. It's the ideal place
    to create the database tables if they don't already exist.
    """
    create_db_and_tables()


# Mount static files and templates for the admin UI
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def root():
    """Welcome endpoint for health checks."""
    return {"message": "Welcome to the Couture Search Shopify App"}


@app.get("/install")
async def install_app(request: Request):
    """
    Redirects the merchant to the Shopify authorization URL to install the app.
    """
    shop = request.query_params.get("shop")
    if not shop:
        return HTMLResponse("Missing 'shop' parameter.", status_code=400)

    print(f"Trying to install with the extension in the shop: {shop}")

    install_url = get_install_url(shop)
    print("Trying to install with the url: ", install_url)
    return RedirectResponse(url=install_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    Handles the callback from Shopify after the merchant authorizes the app.
    Exchanges the authorization code for a permanent access token and saves it.
    """
    shop = request.query_params.get("shop")
    code = request.query_params.get("code")
    host = request.query_params.get("host")

    if not shop or not code:
        return HTMLResponse("Missing 'shop' or 'code' parameter.", status_code=400)

    # Exchange the code for an access token and save it to the database
    access_token = exchange_code_for_token(shop=shop, code=code)

    # Trigger the initial product sync in the background
    trigger_initial_product_sync(shop=shop)

    if access_token:
        print(f"[DEBUG /auth/callback] Got token for {shop}. Saving to DB...")
        save_or_update_token_in_db(shop=shop, access_token=access_token)
        print(f"[DEBUG /auth/callback] Token saved for {shop}.")

    # This is the URL of your app inside the Shopify Admin
    admin_app_url = (
        f"https://admin.shopify.com/store/{shop.replace('.myshopify.com', '')}"
        f"/apps/{settings.SHOPIFY_APP_KEY}"
        f"?shop={shop}&host={host}"  # <--- ADD THIS QUERY STRING
    )

    print(f"Redirecting to final admin URL: {admin_app_url}")

    # Return an HTML response with a script that redirects the top-level window.
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Redirecting...</title>
            <script>
                // This redirect remains the same
                if (window.top == window.self) {{
                    window.location.href = '{admin_app_url}';
                }} else {{
                    window.top.location.href = '{admin_app_url}';
                }}
            </script>
        </head>
        <body>
            <p>Redirecting you to the app...</p>
        </body>
        </html>
    """
    )


@app.post("/api/products/sync")
async def trigger_product_sync(request: Request, body: dict):
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


# --- ADD THIS MIDDLEWARE CODE ---
# @app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware to add Content-Security-Policy headers required by Shopify.
    """
    response = await call_next(request)
    shop = request.query_params.get("shop")

    if shop:
        # Allow framing only by the specific shop's admin page
        response.headers["Content-Security-Policy"] = (
            f"frame-ancestors https://{shop} https://admin.shopify.com;"
        )
    else:
        # For requests without a shop (like the root /), deny framing
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none';"

    return response


# --- END OF MIDDLEWARE CODE ---


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    """Serves the main admin dashboard UI for the app."""
    shop = request.query_params.get("shop")
    host = request.query_params.get("host")  # <-- Get the host parameter

    token_exists = get_shop_access_token(shop)

    if not token_exists:
        # If the host is present, include it in the install redirect
        install_url = f"/install?shop={shop}"
        if host:
            install_url += f"&host={host}"
        return RedirectResponse(url=install_url)

    print(settings.SHOPIFY_APP_KEY, shop, host)

    print("[DEBUG] Serving admin dashboard.")
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "SHOPIFY_API_KEY": settings.SHOPIFY_APP_KEY,
            "shop": shop,
            "host": host,
        },
    )


@app.post("/sync-reco-config")
async def sync_config(shop_details: dict = Depends(verify_shopify_request)):
    """
    Handles the AJAX request from the 'Sync Config' button in the admin dashboard.
    This endpoint is protected and requires a valid session token from App Bridge.
    """
    shop = shop_details["shop"]
    print(f"[DEBUG] /sync-reco-config endpoint called for shop: {shop}")
    try:
        result = sync_reco_configurations(shop)
        return {
            "message": f"Sync successful! {result['created']} created, {result['updated']} updated."
        }
    except Exception as e:
        print(f"[ERROR] Sync failed for shop {shop}: {e}")
        # Return a proper JSON response on error
        return {"error": str(e)}, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
