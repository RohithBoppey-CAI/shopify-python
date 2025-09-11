from fastapi import APIRouter, Request, HTTPException
import httpx
from core.config import settings
from urllib.parse import urlencode

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/reco/{reco_path:path}")
async def proxy_reco_request(
    reco_path: str,
    product_id: int = None,
    query: str = None,
    page_number: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance",
    sort_order: str = "asc",
):
    print("\n--- [PROXY LOG] ---")
    print(f"[PROXY] Received request from theme for path: /{reco_path}")

    base_url = f"{settings.PROXY_SERVER_URL}/{reco_path}"

    params = {}
    if product_id is not None:
        params["product_id"] = product_id
    if query is not None:
        params["query"] = query
    if page_number is not None:
        params["page_number"] = page_number
    if page_number is not None:
        params["page_size"] = page_size
    if sort_by is not None:
        params["sort_by"] = sort_by
    if sort_order is not None:
        params["sort_order"] = sort_order

    query_string = urlencode(params)
    internal_api_url = f"{base_url}?{query_string}"

    print(f"[PROXY] Forwarding request to internal API: {internal_api_url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(internal_api_url)
            response.raise_for_status()
            print(f"[PROXY] Received status {response.status_code} from internal API.")
            print("[PROXY] Success! Forwarding response back to the theme.")
            print("--- [PROXY LOG END] ---\n")
            return response.json()
        except httpx.RequestError as exc:
            print(f"[ERROR] Proxy request to {internal_api_url} failed: {exc}")
            raise HTTPException(
                status_code=502,
                detail="Error connecting to the recommendation service.",
            )
