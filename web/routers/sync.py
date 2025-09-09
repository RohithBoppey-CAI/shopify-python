from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import json
from dependencies.shopify import get_shopify_client_from_query
from services.shopify_product_service import (
    trigger_initial_product_sync,
    trigger_order_history_sync,
    get_last_sync_status,
)
from services.shopify_config_service import sync_reco_configurations
from models import ShopifyAPIClient

router = APIRouter(prefix="/sync", tags=["Synchronization"])


class SyncRequest(BaseModel):
    shop: str


@router.post("/products")
async def trigger_product_sync(
    background_tasks: BackgroundTasks,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """API endpoint to manually trigger a full product catalogue sync."""
    try:
        print("In products sync")
        # Log the "processing" state immediately
        client.update_sync_history(
            key="catalogue_sync_history",
            status="processing",
            message="Full catalogue sync initiated by user.",
        )

        trigger_initial_product_sync(client=client)
        return {"message": "Product catalogue sync completed successfully."}

    except Exception as e:
        error_message = f"Catalogue sync failed: {str(e)}"
        client.update_sync_history(
            key="catalogue_sync_history", status="error", message=error_message
        )
        raise HTTPException(status_code=500, detail=error_message)


@router.post("/orders")
async def trigger_order_sync(
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """API endpoint to manually trigger a full order history sync."""
    if client.is_bulk_operation_running():
        raise HTTPException(
            status_code=409, detail="A sync operation is already in progress."
        )

    client.update_sync_history(
        key="order_sync_history",
        status="processing",
        message="Full order history sync initiated by user.",
    )

    trigger_order_history_sync(client=client)
    return {"message": "Order history sync has been started in the background."}


@router.get("/history/products")
async def get_catalogue_sync_history(
    shop: str,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """Fetches the catalogue sync history from a shop metafield."""
    try:
        history_metafield = client.get_metafield(
            namespace="couture_app", key="catalogue_sync_history"
        )

        if not history_metafield or not history_metafield.get("value"):
            return {"history": []}

        history = json.loads(history_metafield["value"])
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/history/orders")
async def get_order_sync_history(
    shop: str,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """Fetches the order sync history from a shop metafield."""
    try:
        history_metafield = client.get_metafield(
            namespace="couture_app", key="order_sync_history"
        )
        if not history_metafield or not history_metafield.get("value"):
            return {"history": []}
        history = json.loads(history_metafield["value"])
        return {"history": history}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get order history: {str(e)}"
        )


@router.post("/reco-config")
async def sync_reco_config(
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query), body: dict = {}
):
    """Sync recommendation configurations."""
    try:
        result = sync_reco_configurations(client.shop_url, client)
        message = f"Sync successful! {result['created']} created, {result['updated']} updated."

        client.update_sync_history(
            key="reco_config_sync", status="success", message=message
        )

        return {"message": message}
    except Exception as e:
        error_message = f"Sync failed: {str(e)}"
        client.update_sync_history(
            key="reco_config_sync", status="error", message=error_message
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/reco")
async def get_reco_sync_history(
    shop: str,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """Fetches the reco sync history from a shop metafield."""
    try:
        history_metafield = client.get_metafield(
            namespace="couture_app", key="reco_config_sync"
        )

        if not history_metafield or not history_metafield.get("value"):
            return {"history": []}

        history = json.loads(history_metafield["value"])
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.post("/history/clear")
async def clear_all_history(
    shop: str,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """Deletes all sync history metafields for a given shop."""
    try:
        history_keys_to_delete = [
            "catalogue_sync_history",
            "order_sync_history",
            "reco_config_sync",
        ]

        deleted_count = 0
        errors = []

        for key in history_keys_to_delete:
            metafield_to_delete = client.get_metafield(namespace="couture_app", key=key)
            if metafield_to_delete and metafield_to_delete.get("id"):
                try:
                    client.delete_metafield(metafield=metafield_to_delete)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Could not delete '{key}': {e}")

        if errors:
            raise Exception(". ".join(errors))

        return {"message": f"Successfully cleared {deleted_count} history logs."}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear history: {str(e)}"
        )


@router.get("/status")
async def get_sync_status(
    shop: str,
    client: ShopifyAPIClient = Depends(get_shopify_client_from_query),
):
    """API endpoint to check the status of the latest bulk operation."""
    try:
        status = get_last_sync_status(client=client)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
