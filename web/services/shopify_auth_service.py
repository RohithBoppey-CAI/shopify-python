# services/shopify_auth_service.py
import requests
import urllib.parse
from core.config import settings
import base64
from fastapi import Request, HTTPException, status
import hmac
import hashlib

from models.database import SessionLocal, Store


def get_install_url(shop: str) -> str:
    """
    Generates the Shopify authorization URL for the merchant to install the app.
    """
    redirect_uri = f"{settings.APP_URL}/auth/callback"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize"
        f"?client_id={settings.SHOPIFY_APP_KEY}"
        f"&scope={settings.SHOPIFY_APP_SCOPES}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
    )
    return auth_url


def exchange_code_for_token(shop: str, code: str):
    """
    Exchanges a temporary authorization code for a permanent access token.
    In a real application, this token should be securely stored in a database.
    """
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": settings.SHOPIFY_APP_KEY,
        "client_secret": settings.SHOPIFY_APP_SECRET,
        "code": code,
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    access_token = response.json()["access_token"]

    # TODO: Securely save the 'shop' and 'access_token' to your database.
    print(f"Access Token for {shop}: {access_token}")

    # For now, we'll save it to a temporary file for demonstration
    with open(f"./tokens/{shop}_token.txt", "w") as f:
        f.write(access_token)

    return access_token


def get_shop_access_token(shop: str) -> str | None:
    """Retrieves the access token for a given shop from the database."""
    db = SessionLocal()
    try:
        store = db.query(Store).filter(Store.shop_url == shop).first()
        store_access_token = store.access_token if store else None
        # print(store_access_token)
        return store_access_token
    finally:
        db.close()


def save_or_update_token_in_db(shop: str, access_token: str):
    """
    Saves a new token or updates an existing one for a shop in the database.
    """
    db = SessionLocal()
    try:
        print("Saving token in DB")
        # Check if the store already exists
        store = db.query(Store).filter(Store.shop_url == shop).first()
        if store:
            print(f"[DB] Updating token for {shop}")
            store.access_token = access_token
        else:
            print(f"[DB] Creating new record and token for {shop}")
            store = Store(shop_url=shop, access_token=access_token)
            db.add(store)

        db.commit()
        db.refresh(store)
        print(f"[DB] Successfully saved token for {shop}")
    finally:
        db.close()


def verify_shopify_request(request: Request):
    """
    Verifies the authenticity of a request coming from Shopify's frontend (App Bridge).
    This is a crucial security step.
    """
    try:
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1]

        # In a production app, you would decode and verify the JWT here
        # For now, we'll decode it to get the shop domain
        decoded_payload = base64.b64decode(token.split(".")[1] + "==")
        payload_data = eval(decoded_payload.decode("utf-8"))
        shop = payload_data["dest"].replace("https://", "")

        print(f"[DEBUG] Request verified for shop: {shop}")
        return {"shop": shop}

    except Exception as e:
        print(f"[ERROR] Request verification failed: {e}")
        raise HTTPException(status_code=401, detail="Could not verify Shopify request")


def verify_hmac_signature(request: Request):
    """
    Verifies the HMAC signature of an incoming request from Shopify.
    This is the standard way to authenticate non-embedded apps.
    """
    try:
        query_string = request.url.query
        query_params = urllib.parse.parse_qs(query_string)

        # The hmac is the one query parameter we don't include in the calculation
        hmac_from_shopify = query_params.get("hmac", [None])[0]
        if not hmac_from_shopify:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing HMAC signature",
            )

        # Remove hmac and create the message string
        params_for_signature = {k: v[0] for k, v in query_params.items() if k != "hmac"}

        # Sort and encode
        sorted_params = sorted(params_for_signature.items())
        message = urllib.parse.urlencode(
            sorted_params, safe=":/&=", quote_via=urllib.parse.quote
        )

        # Calculate our own signature
        digest = hmac.new(
            settings.SHOPIFY_APP_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures
        if not hmac.compare_digest(digest, hmac_from_shopify):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC signature",
            )

        # If verification passes, return the shop name
        return params_for_signature.get("shop")

    except Exception as e:
        print(f"[ERROR] HMAC verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not verify Shopify request",
        )
