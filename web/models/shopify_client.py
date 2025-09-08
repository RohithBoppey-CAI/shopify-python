import requests
import json
import datetime
from datetime import timezone


class ShopifyAPIClient:
    """
    A client for interacting with the Shopify Admin API (GraphQL).
    """

    def __init__(self, shop_url: str, access_token: str):
        self.shop_url = shop_url
        self.api_version = "2025-04"
        self.graphql_endpoint = (
            f"https://{shop_url}/admin/api/{self.api_version}/graphql.json"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

    def _execute_query(self, query: str, variables: dict = None) -> dict:
        """Executes a GraphQL query/mutation and returns the JSON response."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(
            self.graphql_endpoint, json=payload, headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_bulk_operation_status(self) -> dict:
        """Fetches the status of the current or most recent bulk operation."""
        query = """
        query {
          currentBulkOperation {
            id
            query
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

    def get_shop_gid(self):
        """Helper to get the GraphQL ID of the shop."""
        query = """
        query {
            shop {
                id
            }
        }
        """
        response = self._execute_query(query)
        return response["data"]["shop"]["id"]

    def get_metafield(self, namespace: str, key: str):
        """Gets a specific metafield from the shop."""
        query = """
        query($namespace: String!, $key: String!) {
        shop {
            metafield(namespace: $namespace, key: $key) {
                id
                namespace
                key
                value
                owner {
                    __typename
                    ... on Shop { id }
                    ... on Product { id }
                    ... on Customer { id }
                }
            }
        }
    }
        """
        variables = {"namespace": namespace, "key": key}
        response = self._execute_query(query, variables)
        return response["data"]["shop"]["metafield"]

    def update_sync_history(
        self,
        key: str,
        status: str,
        message: str,
        update_latest_processing: bool = False,
    ):
        """
        Gets, updates, and sets a specific sync history metafield.

        If update_latest_processing is True, it finds and updates the most
        recent 'processing' record. Otherwise, it prepends a new record.
        """
        # 1. Get existing history from the metafield
        existing_history_metafield = self.get_metafield(
            namespace="couture_app", key=key
        )
        history = []
        if existing_history_metafield and existing_history_metafield.get("value"):
            history = json.loads(existing_history_metafield["value"])

        if update_latest_processing:
            # Find the first record with "processing" status and update it.
            updated = False
            for log in history:
                if log.get("status") == "processing":
                    log["status"] = status
                    log["message"] = message
                    # Update the timestamp to reflect the completion time
                    log["timestamp"] = datetime.datetime.now(timezone.utc).isoformat()
                    updated = True
                    break  # Stop after updating the first one

            # If for some reason no "processing" log was found, add a new entry as a fallback.
            if not updated:
                new_log = {
                    "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
                    "status": status,
                    "message": message,
                }
                history.insert(0, new_log)
        else:
            # --- PREPEND LOGIC (for initiating the sync) ---
            new_log = {
                "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
                "status": status,
                "message": message,
            }
            history.insert(0, new_log)

        limited_history = history[:10]

        shop_gid = self.get_shop_gid()
        metafield_input = {
            "ownerId": shop_gid,
            "namespace": "couture_app",
            "key": key,
            "type": "json_string",
            "value": json.dumps(limited_history),
        }

        mutation = """
        mutation($metafields: [MetafieldsSetInput!]!) {
            metafieldsSet(metafields: $metafields) {
                metafields { id }
                userErrors { field message }
            }
        }
        """
        variables = {"metafields": [metafield_input]}
        self._execute_query(mutation, variables)

    def fetch_all_products(self) -> dict:
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
        # print(response)
        return response.get("data", {}).get("bulkOperationRunQuery", {})

    def fetch_all_orders_information(self) -> dict:
        """
        Fetch all the orders information
        """
        bulk_query = """
        mutation {
          bulkOperationRunQuery(
            query: \"""
            {
              orders {
                edges {
                  node {
                    id
                    name
                    createdAt
                    currencyCode
                    totalPriceSet {
                      shopMoney {
                        amount
                        currencyCode
                      }
                    }
                    lineItems(first: 250) {
                      edges {
                        node {
                          id
                          title
                          quantity
                          discountedTotalSet {
                            shopMoney {
                              amount
                              currencyCode
                            }
                          }
                          product {
                            id
                            title
                          }
                          variant {
                            id
                            title
                            sku
                          }
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
        print("Order sync started")
        response = self._execute_query(bulk_query)
        # print(response)
        return response.get("data", {}).get("bulkOperationRunQuery", {})

    # --- METAOBJECT METHODS ---

    def ensure_metaobject_definition(self) -> str:
        """
        Checks if our custom metaobject definition exists. If not, creates it.
        Returns the ID of the definition.
        """
        print("[DEBUG] Checking for existing Metaobject Definition...")
        find_query = """
            query {
                metaobjectDefinitionByType(type: "couture_product_carousel") {
                    id
                }
            }
        """
        response = self._execute_query(find_query)
        existing_definition = response.get("data", {}).get("metaobjectDefinitionByType")

        if existing_definition and existing_definition.get("id"):
            print(f"[DEBUG] Found existing definition: {existing_definition['id']}")
            return existing_definition["id"]

        print("[DEBUG] No existing definition found. Creating a new one...")
        create_mutation = """
            mutation createMetaobjectDefinition($definition: MetaobjectDefinitionCreateInput!) {
                metaobjectDefinitionCreate(definition: $definition) {
                    metaobjectDefinition {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
        """
        variables = {
            "definition": {
                "name": "Couture Product Carousel",
                "type": "couture_product_carousel",
                "fieldDefinitions": [
                    {"name": "Name", "key": "name", "type": "single_line_text_field"},
                    {
                        "name": "Caption",
                        "key": "caption",
                        "type": "single_line_text_field",
                    },
                    {"name": "API Endpoint", "key": "endpoint", "type": "url"},
                    {
                        "name": "Enabled by Default",
                        "key": "enabled_default",
                        "type": "boolean",
                    },
                ],
            }
        }
        response = self._execute_query(create_mutation, variables)
        print(response)
        new_definition = (
            response.get("data", {})
            .get("metaobjectDefinitionCreate", {})
            .get("metaobjectDefinition")
        )

        if new_definition and new_definition.get("id"):
            print(
                f"[DEBUG] Successfully created new definition: {new_definition['id']}"
            )
            return new_definition["id"]
        else:
            errors = (
                response.get("data", {})
                .get("metaobjectDefinitionCreate", {})
                .get("userErrors", [])
            )
            raise Exception(f"Could not create metaobject definition: {errors}")

    # In web/models/shopify_client.py

    def upsert_metaobject(self, definition_id: str, reco_data: dict) -> str:
        """
        Creates or updates a Metaobject entry for a specific product carousel.
        """
        handle = reco_data["banner_name"].lower().replace(" ", "-")
        print(f"[DEBUG] Upserting metaobject for handle: {handle}")

        mutation = """
            mutation metaobjectUpsert($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
                metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
                    metaobject {
                        id
                        handle
                        updatedAt
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
        """
        variables = {
            "handle": {"type": "couture_product_carousel", "handle": handle},
            "metaobject": {
                "fields": [
                    {"key": "name", "value": reco_data.get("banner_name")},
                    {"key": "caption", "value": reco_data.get("caption")},
                    {"key": "endpoint", "value": reco_data.get("endpoint")},
                    {
                        "key": "enabled_default",
                        "value": str(reco_data.get("enabled", False)).lower(),
                    },
                ]
            },
        }

        response = self._execute_query(mutation, variables)

        # print(response)

        # Check if the API call itself had top-level errors
        if "errors" in response:
            print(f"[ERROR] GraphQL query failed: {response['errors']}")
            return "failed"

        upsert_data = response.get("data", {}).get("metaobjectUpsert", {})

        if upsert_data and upsert_data.get("metaobject"):
            return "updated"
        else:
            errors = upsert_data.get("userErrors", [])
            print(f"[ERROR] Failed to upsert metaobject '{handle}': {errors}")
            return "failed"

    def delete_metafield(self, metafield: dict):
        """
        Deletes a metafield using metafieldsDelete (requires ownerId, namespace, key).
        """
        mutation = """
        mutation MetafieldsDelete($metafields: [MetafieldIdentifierInput!]!) {
        metafieldsDelete(metafields: $metafields) {
            deletedMetafields {
            key
            namespace
            ownerId
            }
            userErrors {
            field
            message
            }
        }
        }
        """

        variables = {
            "metafields": [
                {
                    "ownerId": metafield["owner"]["id"],
                    "namespace": metafield["namespace"],
                    "key": metafield["key"],
                }
            ]
        }

        response = self._execute_query(mutation, variables)
        print("Shopify API response:", response)

        errors = (
            response.get("data", {}).get("metafieldsDelete", {}).get("userErrors", [])
        )
        if errors:
            raise Exception(f"Failed to delete metafield {metafield['key']}: {errors}")

        return response

    def get_access_scopes(self) -> list:
        """
        Makes a GraphQL query to Shopify to get the list of scopes
        associated with the access token being used.
        """
        query = """
        query {
            appInstallation {
                accessScopes {
                    handle
                }
            }
        }
        """
        response = self._execute_query(query)
        scopes = (
            response.get("data", {}).get("appInstallation", {}).get("accessScopes", [])
        )

        # Extract just the string handles from the response
        return [scope["handle"] for scope in scopes]
