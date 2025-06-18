from fastapi import FastAPI, Request
from utils.shopify import get_all_product_ids, get_store_token_id
import os
import uvicorn
from fastapi.responses import RedirectResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/get-product-catalogue")
async def get_product_catalogue(request: dict):
    result = get_all_product_ids(request)
    return result


@app.post("/install")
async def install_app(request: dict):
    # this is the function that gets executed when a store / user installs our application
    # the merchant will be getting a request to authorize our application
    install_url = get_store_token_id(request)
    print(install_url)
    return RedirectResponse(url=install_url)


@app.get("/auth/callback")
def auth_callback(request: Request):
    print(request)
    shop = request.query_params.get("shop")
    code = request.query_params.get("code")

    print(shop)
    print(code)
    
    # token_response = requests.post(
    #     f"https://{shop}/admin/oauth/access_token",
    #     json={
    #         "client_id": SHOPIFY_API_KEY,
    #         "client_secret": SHOPIFY_API_SECRET,
    #         "code": code
    #     }
    # )

    # token_data = token_response.json()
    # access_token = token_data["access_token"]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
