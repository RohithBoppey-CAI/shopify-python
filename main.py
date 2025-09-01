from fastapi import FastAPI, Request
from utils.shopify import (
    get_all_product_catalogue,
    store_app_auth_init,
    get_store_access_token,
    get_last_bulk_operation_status,
)
import os
import uvicorn
from fastapi.responses import RedirectResponse

from routers import template_router

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/get-product-catalogue")
async def get_product_catalogue(request: dict):
    result = get_all_product_catalogue(
        request,
        wait=True,
        save=True,
        save_file_name="products.json",
    )
    return result


@app.post("/install")
async def install_app(request: dict):
    # this is the function that gets executed when a store / user installs our application
    # the merchant will be getting a request to authorize our application
    install_url = store_app_auth_init(request)
    print(install_url)
    return RedirectResponse(url=install_url)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    This gets executed once the app has been added and approved by the store admin from the "Install app into your store" page
    """
    print("App has been authenticated successfully, In callback function now!")
    token_result = get_store_access_token(request)

    # trigger download in the background
    status_message = get_all_product_catalogue(token_result, wait=False)

    message = {
        "status": "Products downloading started in background",
        "status_message": status_message,
        "credentials": token_result,
    }
    print(message)
    store = token_result.get("store", None)

    return RedirectResponse(url=f"/get-started?store={store}")


@app.post("/last-bulk-operation")
async def get_last_bulk_operation(request: dict):
    """
    Check the status of the last bulk operation
    """
    print("Checking the status of the last bulk operation")
    return get_last_bulk_operation_status(request)


app.include_router(template_router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
