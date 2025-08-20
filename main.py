# main.py
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.config import settings
from services import shopify_auth_service, shopify_product_service
# from models.database import SessionLocal, engine, Base

# Create database tables
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Couture Search Shopify App",
    description="API for handling Shopify integration and providing recommendation services.",
    version="1.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency for database sessions
# def get_db():
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()

@app.get("/")
async def root():
    """Welcome endpoint."""
    return {"message": "Welcome to the Couture Search Shopify App"}

@app.get("/install")
async def install_app(shop: str):
    """
    Redirects the merchant to the Shopify authorization URL to install the app.
    The 'shop' parameter is provided by Shopify when the installation process begins.
    """
    install_url = shopify_auth_service.get_install_url(shop)
    return RedirectResponse(url=install_url)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    Handles the callback from Shopify after the merchant authorizes the app.
    Exchanges the authorization code for a permanent access token.
    """
    shop = request.query_params.get("shop")
    code = request.query_params.get("code")

    # Exchange the code for an access token and save it
    shopify_auth_service.exchange_code_for_token(shop=shop, code=code)

    # Trigger the initial product sync in the background
    shopify_product_service.trigger_initial_product_sync(shop=shop)
    
    # Redirect to the app's welcome page
    return {"shop": shop}

@app.post("/api/products/sync")
async def trigger_product_sync(request: Request, body: dict):
    """API endpoint to manually trigger a full product catalogue sync."""
    # In a real app, you'd get the shop from the request context (e.g., JWT)
    # For now, we'll assume it's in the headers or body
    data = await request.json()
    shop = data.get("shop")
    result = shopify_product_service.trigger_initial_product_sync(shop=shop)
    return result

@app.get("/api/sync/status")
async def get_sync_status(shop: str):
    """API endpoint to check the status of the latest bulk operation."""
    status = shopify_product_service.get_last_sync_status(shop=shop)
    return status

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
