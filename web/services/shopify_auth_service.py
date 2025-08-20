# services/shopify_auth_service.py
import requests
import urllib.parse
from core.config import settings

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
    with open(f"{shop}_token.txt", "w") as f:
        f.write(access_token)
