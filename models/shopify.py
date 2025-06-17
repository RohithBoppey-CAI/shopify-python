import os
import requests
from dotenv import load_dotenv
import asyncio
import httpx
import time

load_dotenv()


class ShopifyAPIClient:
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

        status_query = """
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
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
        while True:
            response = requests.post(
                self.graphql_endpoint, headers=headers, json={"query": status_query}
            )
            result = response.json()
            op = result.get("data", {}).get("currentBulkOperation", {})
            print(f"Status: {op.get('status')}")
            if op.get("status") == "COMPLETED":
                print(f"✅ Bulk operation completed. Download URL: {op.get('url')}")
                return op.get("url")
            if op.get("status") in ("FAILED", "CANCELED"):
                print(f"❌ Bulk operation failed: {op.get('errorCode')}")
                raise Exception(f"Bulk operation {op.get('status')}")
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

    def execute_bulk_operations(self, query: str, wait=False):
        result = {}
        # bulk_operation_id = self.start_bulk_operation(bulk_graphql_query=query)
        # result["operation_id"] = bulk_operation_id
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


if __name__ == "__main__":
    client = ShopifyAPIClient(asyncr=True)
    client.fetch_sample_products(limit=20)
