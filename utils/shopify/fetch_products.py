from models.shopify import ShopifyAPIClient, ShopifyAppClient
from ..commons.api_utils import read_jsonl_from_url
from ..commons.file_utils import save_to_json


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


def get_all_product_catalogue(
    request: dict,
    save_file_name: str = "file.json",
    url_key="output_url",
    wait=False,
    save=False,
):
    try:
        shop_id = request.get("store", None)
        access_token = request.get("access_token", None)

        if not shop_id or not access_token:
            raise Exception("Non valid shop id or access token given")

        client = ShopifyAPIClient(shop_url=shop_id, access_token=access_token)

        # TODO: insert the details in the DB
        details = client.fetch_product_catalogue_details(wait=wait)

        # read from the endpoint into json and return it if waiting is enabled
        if wait and url_key in details:
            print("Found the URL in the response, reading it to give products!")
            all_objects = read_jsonl_from_url(details[url_key])
            if save:
                save_to_json(filename=save_file_name, data_dict=all_objects)
            return all_objects
        else:
            return details

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
        query_params = request.query_params
        shop = query_params.get("shop", "shop")
        code = query_params.get("code", "shop")

        access_token = client.return_shopify_store_access_token(shop, code)

        # TODO: store it in DB
        return {"store": shop, "access_token": access_token}

    except Exception as e:
        print(f"Exception in generating store access token: {e}")


# if __name__ == "__main__":
#     LIMIT = 20
#     res = get_all_product_ids(LIMIT)
#     print(res)
