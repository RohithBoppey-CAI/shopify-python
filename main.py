from fastapi import FastAPI, Request
from utils.shopify import (
    get_all_product_catalogue,
    store_app_auth_init,
    get_store_access_token,
)
import os
import uvicorn
from fastapi.responses import RedirectResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/get-product-catalogue")
async def get_product_catalogue(request: dict):
    result = get_all_product_catalogue(request, wait=True)
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
    token_result = get_store_access_token(request)

    # trigger download in the background
    status_message = get_all_product_catalogue(token_result, wait=False)

    return {
        "status": "Products downloading started in background",
        "status_message": status_message,
        "credentials": token_result,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
