from fastapi import FastAPI
from utils.shopify import get_all_product_ids
app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/get-product-catalogue")
async def get_product_catalogue(request: dict):
    result = get_all_product_ids(request)
    return result
