import os
import requests
from dotenv import load_dotenv
import asyncio
import httpx
import time
import urllib

load_dotenv()


class ShopifyAPIClient:
    """
    This is to access the store level functions
    - like downloading catalogue from a store
    """

    def __init__(self, shop_url=None, access_token=None, asyncr=False):
        self.shop_url = shop_url or os.getenv("SHOP_URL", "your-store.myshopify.com")
        self.access_token = access_token or os.getenv(
            "ACCESS_TOKEN", "your-access-token"
        )
        self.graphql_endpoint = (
            f"https://{self.shop_url}/admin/api/2025-04/graphql.json"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
        self.asyncr = asyncr
        print("Shopify client created")

    def execute_graphql_query(self, query):
        """
        Takes in the graphql request body and makes the API request
        """
        try:
            response = requests.post(
                self.graphql_endpoint, json={"query": query}, headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
            return None

    async def execute_graphql_query_async(self, query):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.graphql_endpoint,
                    json={"query": query},
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            print("Request failed (async):", e)
            return None

    # single function to run both syncronously and asyncronously
    def execute_query(self, query):
        def _run_async(coro):
            return asyncio.run(coro)

        if self.asyncr:
            return _run_async(self.execute_graphql_query_async(query))
        else:
            return self.execute_graphql_query(query)

    def start_bulk_operation(self, bulk_graphql_query):
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
        response = requests.post(
            self.graphql_endpoint,
            headers=headers,
            json={"query": bulk_graphql_query},
        )
        data = response.json()
        print("Bulk Operation Started: ", data)
        bulk_op = (
            data.get("data", {})
            .get("bulkOperationRunQuery", {})
            .get("bulkOperation", {})
        )
        return bulk_op.get("id")

    def wait_for_bulk_operation_to_complete(self):
        POLL_INTERVAL_SEC = 5
        print("⏳ Waiting for bulk operation to complete...")
        while True:
            op = self.is_bulk_operation_running(return_op=True)
            status = op.get("status")
            print(f"Status: {status}")
            if status == "COMPLETED":
                print(f"✅ Bulk operation completed. Download URL: {op.get('url')}")
                return op.get("url")

            if status in ("FAILED", "CANCELED"):
                print(f"❌ Bulk operation failed: {op.get('errorCode')}")
                raise Exception(f"Bulk operation {status}")

            time.sleep(POLL_INTERVAL_SEC)

    def fetch_sample_products(self, limit=20):
        try:
            query = f"""
                query {{
                    inventoryItems(first: {limit}) {{
                        edges {{
                            node {{
                                id
                                tracked
                                sku
                            }}
                        }}
                    }}
                }}
            """
            results = self.execute_query(query)
            return results

        except Exception as e:
            print(f"Failed to fetch products: {e}")

    def is_bulk_operation_running(self, return_op=False):
        query = """
        query {
            currentBulkOperation(type: QUERY) {
                id
                status
                errorCode
                createdAt
                completedAt
                objectCount
                fileSize
                url
            }
        }
        """
        try:
            data = self.execute_query(query)
            op = data.get("data", {}).get("currentBulkOperation", {})
            if return_op:
                return op
            return op.get("status") not in (None, "COMPLETED", "FAILED", "CANCELED")
        except requests.exceptions.RequestException as e:
            print("Failed to check bulk operation status:", e)
            return False if not return_op else {}

    def execute_bulk_operations(self, query: str, wait=False):
        result = {}
        if not self.is_bulk_operation_running():
            bulk_operation_id = self.start_bulk_operation(bulk_graphql_query=query)
            result["operation_id"] = bulk_operation_id
        else:
            raise ("⚠️ A bulk operation is already running. Skipping new operation.")

        result_endpoint = self.wait_for_bulk_operation_to_complete() if wait else None
        result["output_url"] = result_endpoint
        return result

    def fetch_product_catalogue_details(self, wait=False):
        query = """
            mutation {
                bulkOperationRunQuery(
                    query: \"""
                    {
                    products {
                        edges {
                        node {
                            id
                            title
                            handle
                            descriptionHtml
                            productType
                            vendor
                            tags
                            status
                            variants {
                            edges {
                                node {
                                id
                                title
                                sku
                                inventoryQuantity
                                price 
                                }
                            }
                            }
                            images {
                            edges {
                                node {
                                originalSrc
                                altText
                                }
                            }
                            }
                        }
                        }
                    }
                    }
                    \"""
                ) {
                    bulkOperation {
                    id
                    status
                    }
                    userErrors {
                    field
                    message
                    }
                }
            }
        """

        return self.execute_bulk_operations(query, wait)


class ShopifyAppClient:
    def __init__(
        self, client_id=None, client_secret=None, scopes=None, redirect_url=None
    ):
        self.client_id = client_id or os.getenv("SHOPIFY_APP_KEY", "your-client-id")
        self.client_secret = client_secret or os.getenv(
            "SHOPIFY_APP_SECRET", "your-client-secret"
        )
        self.scopes = scopes or os.getenv(
            "SHOPIFY_APP_SCOPES", "read_products,write_orders"
        )
        self.redirect_url = redirect_url or os.getenv(
            "SHOPIFY_APP_REDIRECT_URL", "https://yourapp.com/callback"
        )

        if isinstance(scopes, str):
            self.scopes = scopes.split(",")

        print("Shopify APP Client initialized")

    def return_app_install_url(self, store: str = None):
        try:
            if not store:
                raise ("No store found")
            install_url = (
                f"https://{store}/admin/oauth/authorize"
                f"?client_id={self.client_id}"
                f"&scope={self.scopes}"
                f"&redirect_uri={urllib.parse.quote(self.redirect_url)}"
            )
            return install_url
        except Exception as e:
            print(f"Exception in creating store url: {e}")

    def return_shopify_store_access_token(self, shop: str, code: str):
        """
        Use the shop and code to create and return the access token
        """
        admin_url = f"https://{shop}/admin/oauth/access_token"
        token_response = requests.post(
            admin_url,
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
            },
        )

        token_data = token_response.json()
        access_token = token_data["access_token"]
        return access_token


if __name__ == "__main__":
    client = ShopifyAPIClient(asyncr=True)
    client.fetch_sample_products(limit=20)
