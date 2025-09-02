import requests
import time


class ShopifyAPIClient:
    """
    A client for interacting with the Shopify Admin API (GraphQL).
    """

    def __init__(self, shop_url: str, access_token: str):
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

    def upsert_metaobject(self, definition_id: str, reco_data: dict) -> str:
        """
        Creates or updates a Metaobject entry for a specific product carousel.
        """
        handle = reco_data['banner_name'].lower().replace(' ', '-')
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
            "handle": {
                "type": "couture_product_carousel",
                "handle": handle
            },
            "metaobject": {
                "definitionId": definition_id,
                "fields": [
                    {"key": "name", "value": reco_data.get('banner_name')},
                    {"key": "caption", "value": reco_data.get('caption')},
                    {"key": "endpoint", "value": reco_data.get('endpoint')},
                    {"key": "enabled_default", "value": str(reco_data.get('enabled', False)).lower()}
                ]
            }
        }
        response = self._execute_query(mutation, variables)
        upsert_data = response.get("data", {}).get("metaobjectUpsert", {})
        
        if upsert_data.get("metaobject"):
            return 'updated' if upsert_data["metaobject"]["updatedAt"] else 'created'
        else:
            errors = upsert_data.get("userErrors", [])
            print(f"[ERROR] Failed to upsert metaobject '{handle}': {errors}")
            return 'failed'
