import json

class PostmanCollectionUseCase:
    def __init__(self):
        pass

    import json
import os

def convert_to_postman_collection(spec_file_path: str, output_file_path: str):
    with open(spec_file_path, 'r') as f:
        spec = json.load(f)

    collection = {
        "info": {
            "name": "Game API Collection",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "auto-generated-id"
        },
        "item": []
    }

    for endpoint in spec["endpoints"]:
        url = endpoint["endpointName"]
        method = endpoint["method"].upper()
        description = endpoint.get("description", "")
        auth_required = endpoint.get("authRequired", False)
        query_params = endpoint.get("queryParams", {})
        payload = endpoint.get("payload_sample", {})

        headers = []
        if method in ["POST", "PUT", "PATCH"]:
            headers.append({
                "key": "Content-Type",
                "value": "application/json"
            })

        if auth_required:
            headers.append({
                "key": "Authorization",
                "value": "Bearer {{auth_token}}"
            })

        # Request URL & Params
        url_object = {
            "raw": "{{base_url}}" + url,
            "host": ["{{base_url}}"],
            "path": url.lstrip("/").split("/"),
            "query": [
                {
                    "key": key,
                    "value": "",
                    "description": val.get("description", "")
                }
                for key, val in query_params.items()
            ]
        }

        request = {
            "method": method,
            "header": headers,
            "url": url_object,
            "description": description
        }

        if method in ["POST", "PUT", "PATCH"]:
            request["body"] = {
                "mode": "raw",
                "raw": json.dumps(payload, indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }

        collection["item"].append({
            "name": f"{method} {url}",
            "request": request
        })

    with open(output_file_path, "w") as f:
        json.dump(collection, f, indent=2)

    print(f"✅ Postman collection saved to {output_file_path}")

    async def execute(self, file_path: str):
        
        # Get the directory of the input file
        input_dir = os.path.dirname(file_path)
        
        # Create the output file path in the same directory with name "postman_collection.json"
        output_file_path = os.path.join(input_dir, "postman_collection.json")
        
        # Call the function to convert and save the collection
        convert_to_postman_collection(file_path, output_file_path)
        
        return output_file_path