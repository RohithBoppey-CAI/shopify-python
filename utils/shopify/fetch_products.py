from models.shopify import ShopifyAPIClient
from ..commons.api_utils import read_jsonl_from_url


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


def get_all_product_ids(request: dict, url_key = "output_url"):
    try:
        shop_id = request.get("shop_id", None)
        access_token = request.get("access_token", None)

        if not shop_id or not access_token:
            raise ("Non valid shop id or access token given")

        client = ShopifyAPIClient(shop_url=shop_id, access_token=access_token)
        details = client.fetch_product_catalogue_details(wait=True)

        # read from the endpoint into json and return it
        all_objects = read_jsonl_from_url(details[url_key])

        return all_objects
    except Exception as e:
        print(f"Error occurred in getting product catalogue info: {e}")


# if __name__ == "__main__":
#     LIMIT = 20
#     res = get_all_product_ids(LIMIT)
#     print(res)
