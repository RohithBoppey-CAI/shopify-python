import requests
import time

class ShopifyAPIClient:
    """
    A client for interacting with the Shopify Admin API (GraphQL).
    """
    def __init__(self, shop_url: str, access_token: str):
        self.api_version = "2025-04"
        self.graphql_endpoint = f"https://{shop_url}/admin/api/{self.api_version}/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

    def _execute_query(self, query: str) -> dict:
        """Executes a GraphQL query and returns the JSON response."""
        response = requests.post(self.graphql_endpoint, json={"query": query}, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_bulk_operation_status(self) -> dict:
        """Fetches the status of the current or most recent bulk operation."""
        query = """
        query {
          currentBulkOperation {
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
        response = self._execute_query(query)
        return response.get("data", {}).get("currentBulkOperation", {})

    def is_bulk_operation_running(self) -> bool:
        """Checks if a bulk operation is currently running."""
        op = self.get_bulk_operation_status()
        if not op:
            return False
        return op.get("status") not in ("COMPLETED", "FAILED", "CANCELED")

    def fetch_all_products(self, wait: bool = False) -> dict:
        """
        Initiates a bulk query to fetch all products and their variants.
        """
        bulk_query = """
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
        response = self._execute_query(bulk_query)
        print(response)
        return response.get("data", {}).get("bulkOperationRunQuery", {})
