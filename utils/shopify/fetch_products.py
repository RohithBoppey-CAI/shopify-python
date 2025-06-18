from models.shopify import ShopifyAPIClient, ShopifyAppClient
from ..commons.api_utils import read_jsonl_from_url
from dotenv import load_dotenv

load_dotenv()


def extract_inventory_response_basic(data):
    all_products = []
    try:
        edges = data.get("data", {}).get("inventoryItems", {}).get("edges", [])
        for product in edges:
            link = product.get("node", {}).get("id", "")
            prod_id = link.split("/")[-1] if link else None
            if prod_id:
                all_products.append(prod_id)
    except Exception as e:
        print("Error extracting response:", e)
    return all_products


def get_all_product_ids(request: dict, url_key="output_url"):
    try:
        shop_id = request.get("shop_id", None)
        access_token = request.get("access_token", None)

        if not shop_id or not access_token:
            raise ("Non valid shop id or access token given")

        client = ShopifyAPIClient(shop_url=shop_id, access_token=access_token)

        # TODO: insert the details in the DB
        details = client.fetch_product_catalogue_details(wait=True)

        # read from the endpoint into json and return it
        all_objects = read_jsonl_from_url(details[url_key])

        return all_objects
    except Exception as e:
        print(f"Error occurred in getting product catalogue info: {e}")


def store_app_auth_init(request: dict):
    try:
        store = request.get("store", None)
        client = ShopifyAppClient()
        return client.return_app_install_url(store=store)

    except Exception as e:
        print(f"Exception in bringing store access id: {e}")


def get_store_access_token(request: dict):
    try:
        client = ShopifyAppClient()
        shop = request.get("shop")
        code = request.get("code")
        access_token = client.return_shopify_store_access_token(shop, code)
        # TODO: store it in DB
        return {"store": shop, "access_token": access_token}

    except Exception as e:
        print(f"Exception in generating store access token: {e}")


# if __name__ == "__main__":
#     LIMIT = 20
#     res = get_all_product_ids(LIMIT)
#     print(res)
