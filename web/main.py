from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from models.database import create_db_and_tables, create_folders, remove_shopify_db
from services.shopify_auth_service import (
    verify_hmac_signature,
    get_shop_access_token,
    get_shop_api_key,
)
from routers import auth_router, sync_router, api_router

app = FastAPI(title="Couture Search Shopify App")


# Event Handlers
@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup"""
    remove_shopify_db()
    create_db_and_tables()
    create_folders(folders=["downloads", "tokens"])


# remove the shopify db on closing the application
@app.on_event("shutdown")
def on_shutdown():
    """Cleanup actions on shutdown"""
    remove_shopify_db()


# CORS Configuration
origins = [
    "https://dummycouture.myshopify.com",
    "https://admin.shopify.com",
    "*",  # contains the list of stores
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template Configuration
templates = Jinja2Templates(directory="templates")

# Include Routers - group related endpoints
app.include_router(auth_router, tags=["Authentication"])

app.include_router(sync_router, tags=["Synchronization"])

app.include_router(api_router, tags=["API"])


@app.get("/")
async def root():
    """Welcome endpoint for health checks."""
    return {"message": "Welcome to the Couture Search Shopify App"}


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    shop: str = Depends(verify_hmac_signature),
    api_key: str = Depends(get_shop_api_key),
):
    """Serves the main admin dashboard UI for the app, protected by HMAC verification."""
    if not shop:
        return HTMLResponse(
            "Could not verify the request came from Shopify.", status_code=403
        )

    token_exists = get_shop_access_token(shop)
    if not token_exists:
        return RedirectResponse(url=f"/auth/install?shop={shop}")

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request, "api_key": api_key},
    )
