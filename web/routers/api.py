from fastapi import APIRouter, Request, HTTPException
import httpx
from core.config import settings
from utils.commons.api_utils import return_dummy_handlers

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/reco/{reco_path:path}")
async def proxy_reco_request(reco_path: str, product_id: int = None, query: str = None):
    """This endpoint acts as a proxy to the internal recommendation service."""
    print("\n--- [PROXY LOG] ---")
    print(f"[PROXY] Received request from theme for path: /{reco_path}")

    internal_api_url = f"{settings.PROXY_SERVER_URL}/{reco_path}"
    if product_id:
        internal_api_url += f"?product_id={product_id}"
    if query:
        internal_api_url += f"?query={query}"
    print(f"[PROXY] Forwarding request to internal API: {internal_api_url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(internal_api_url)
            response_json = response.json()
            print(f"[PROXY] Received status {response.status_code} from internal API.")
            response.raise_for_status()
            print("[PROXY] Success! Forwarding response back to the theme.")
            print("--- [PROXY LOG END] ---\n")
            return response_json
        except httpx.RequestError as exc:
            print(f"[ERROR] Proxy request to {internal_api_url} failed: {exc}")
            raise HTTPException(
                status_code=502,
                detail="Error connecting to the recommendation service.",
            )
