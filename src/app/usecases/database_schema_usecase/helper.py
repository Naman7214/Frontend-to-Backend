import json
import re
# import logging # Removed logging import
import requests
from typing import Dict, Any, List
from src.app.repositories.database_schema_repo import DatabaseRepository # Added import

from src.app.services.openai_service import OpenAIService
from src.app.config.settings import settings
from fastapi import Depends
from src.app.prompts.database_schema_prompt import DATABASE_SCHEMA_USER_PROMPT, DATABASE_SCHEMA_SYSTEM_PROMPT
from src.app.services.api_service import ApiService

class DatabaseSchemaHelper:
    def __init__(self, openai_client: OpenAIService = Depends(), db_repo: DatabaseRepository = Depends(), api_service: ApiService = Depends()): # Changed db to db_repo
        self.openai_client = openai_client
        # self.model = settings.OPENAI_MODEL
        self.database_schema_user_prompt = DATABASE_SCHEMA_USER_PROMPT
        self.database_schema_system_prompt = DATABASE_SCHEMA_SYSTEM_PROMPT
        self.mock_data_api_url = settings.MOCK_DATA_API_URL
        self.api_service = api_service
        self.db_repo = db_repo # Changed db to db_repo

    def extract_schema_info(self, endpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract schema information from endpoint data.
        """
        return {
            "collection_name": endpoint_data.get("collection_name", "unknown"),
            "schema": endpoint_data.get("schema", {}),
            "samples": endpoint_data.get("samples", {})
        }
        
    async def analyze_endpoint_schema(self, endpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = self.database_schema_user_prompt.format(
            endpointName=endpoint_data["endpointName"],
            method=endpoint_data["method"],
            description=endpoint_data["description"],
            payload=json.dumps(endpoint_data["payload"], indent=2),
            response=json.dumps(endpoint_data["response"], indent=2)
        )
        
        try:
            content = await self.openai_client.completions(
                user_prompt=user_prompt,
                system_prompt=self.database_schema_system_prompt,
                temperature=0.5,
            )
            
            json_match = re.search(r'{.*}', content, re.DOTALL)
            if json_match:
                schema_json_str = json_match.group(0)
            else:
                schema_json_str = content # Fallback, or could be an error
            
            schema_json = json.loads(schema_json_str.strip())
            return schema_json
        
        except Exception as e:
            print(f"Error in analyze_endpoint_schema for endpoint {endpoint_data.get('endpointName', 'Unknown')}: {str(e)}")
            return {
                "collection_name": "unknown",
                "schema": {},
                "samples": {},
            }

    async def generate_mock_data(self, schema_info: Dict[str, Any], num_records: int = 10) -> Dict[str, Any]: # Add async
        """
        Call external API to generate mock data based on the schema.
        Note: num_records is printed but not used in the API call itself in this version.
        """
        try:
            # Add await and expect direct JSON response or exception
            mock_data = await self.api_service.post(
                url=self.mock_data_api_url,
                data=schema_info.get("samples", {})
            )
            
            # If post is successful, mock_data is the JSON response.
            # The api_service.post method raises HTTPException on API errors.
            print(f"Generated mock records for collection {schema_info.get('collection_name', 'unknown')}. Target: {num_records} (actual count may vary based on API).")
            return mock_data
        
        except Exception as e:
            # This will catch HTTPErrors from api_service.post or other exceptions
            print(f"Error generating mock data for {schema_info.get('collection_name', 'unknown')}: {str(e)}") # Replaced logging
            return {"data": [], "error": str(e)}
    
    def insert_to_mongodb(self, repo_path: str, collection_name: str, data: List[Dict[str, Any]]) -> bool: # Added repo_path
        """
        Insert mock data into MongoDB.
        Database and collection are determined by repo_path and collection_name.
        """
        if self.db_repo is None:
            print("DatabaseRepository instance not available. Skipping database insertion.") # Replaced logging
            return False
            
        if not data:
            print(f"No data provided to insert into collection {collection_name}") # Replaced logging
            return False
        
        if not collection_name or not isinstance(collection_name, str):
            print(f"Invalid collection name: {collection_name}. Skipping insertion.") # Replaced logging
            return False

        try:
            db = self.db_repo.initialize_db_from_repo_path(repo_path)
            if db is None: # Should not happen if initialize_db_from_repo_path is robust
                print(f"Failed to initialize database using repo path '{repo_path}'. Skipping insertion.")
                return False

            if collection_name in db.list_collection_names():
                print(f"Collection '{collection_name}' in database '{db.name}' already exists. Dropping existing collection.") # Replaced logging
                db[collection_name].drop()
            
            collection = self.db_repo.create_collection(db, collection_name)
            inserted_ids = self.db_repo.insert_many(collection, data) # Use repository's insert_many
            print(f"Successfully inserted {len(inserted_ids)} documents into collection '{collection_name}' in database '{db.name}'") # Replaced logging
            return True
        except Exception as e:
            print(f"Error inserting data into MongoDB collection '{collection_name}' in database for repo '{repo_path}': {str(e)}") # Replaced logging
            return False
