from fastapi import FastAPI
from utils.shopify import get_all_product_ids
import os
import uvicorn

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/get-product-catalogue")
async def get_product_catalogue(request: dict):
    result = get_all_product_ids(request)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
