from fastapi import Header, HTTPException


def validate_shopify_incoming_request(
    x_api_key: str = Header(...), x_store_identifier: str = Header(...)
):
    print(f"API_KEY: {x_api_key} | STORE: {x_store_identifier}")
    if not x_api_key or not x_store_identifier:
        raise HTTPException(status_code=400, detail="Missing headers")

    if "COUTURE" not in x_api_key or "myshopify.com" not in x_store_identifier:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # If everything is good, just return True (or nothing)
    return True
