import json
import re
import asyncio
from typing import Dict, Any, List
from src.app.repositories.database_schema_repo import DatabaseRepository

from src.app.services.openai_service import OpenAIService
from src.app.config.settings import settings
from fastapi import Depends
from src.app.prompts.database_schema_prompt import DATABASE_SCHEMA_USER_PROMPT, DATABASE_SCHEMA_SYSTEM_PROMPT
from src.app.services.api_service import ApiService

class DatabaseSchemaHelper:
    def __init__(self, openai_client: OpenAIService = Depends(), db_repo: DatabaseRepository = Depends(), api_service: ApiService = Depends()):
        self.openai_client = openai_client
        # self.model = settings.OPENAI_MODEL
        self.database_schema_user_prompt = DATABASE_SCHEMA_USER_PROMPT
        self.database_schema_system_prompt = DATABASE_SCHEMA_SYSTEM_PROMPT
        self.mock_data_api_url = settings.MOCK_DATA_API_URL
        self.api_service = api_service
        self.db_repo = db_repo
        # Semaphore to limit concurrent API calls if needed
        self.semaphore = asyncio.Semaphore(10)  # Adjust number based on API limits

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
        """Analyze endpoint schema using OpenAI"""
        async with self.semaphore:  # Limit concurrent API calls
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

    async def generate_mock_data(self, schema_info: Dict[str, Any], num_records: int = 10) -> Dict[str, Any]:
        """
        Call external API to generate mock data based on the schema.
        """
        async with self.semaphore:  # Limit concurrent API calls
            try:
                # Add await and expect direct JSON response or exception
                mock_data = await self.api_service.post(
                    url=self.mock_data_api_url,
                    data=schema_info.get("samples", {})
                )
                
                print(f"Generated mock records for collection {schema_info.get('collection_name', 'unknown')}. Target: {num_records} (actual count may vary based on API).")
                return mock_data
            
            except Exception as e:
                print(f"Error generating mock data for {schema_info.get('collection_name', 'unknown')}: {str(e)}")
                return {"data": [], "error": str(e)}
    
    def insert_to_mongodb(self, repo_path: str, collection_name: str, data: List[Dict[str, Any]]) -> bool:
        """
        Synchronous version of MongoDB insertion (kept for backward compatibility)
        """
        if self.db_repo is None:
            print("DatabaseRepository instance not available. Skipping database insertion.")
            return False
            
        if not data:
            print(f"No data provided to insert into collection {collection_name}")
            return False
        
        if not collection_name or not isinstance(collection_name, str):
            print(f"Invalid collection name: {collection_name}. Skipping insertion.")
            return False

        try:
            db = self.db_repo.initialize_db_from_repo_path(repo_path)
            if db is None:
                print(f"Failed to initialize database using repo path '{repo_path}'. Skipping insertion.")
                return False

            if collection_name in db.list_collection_names():
                print(f"Collection '{collection_name}' in database '{db.name}' already exists. Dropping existing collection.")
                db[collection_name].drop()
            
            collection = self.db_repo.create_collection(db, collection_name)
            inserted_ids = self.db_repo.insert_many(collection, data)
            print(f"Successfully inserted {len(inserted_ids)} documents into collection '{collection_name}' in database '{db.name}'")
            return True
        except Exception as e:
            print(f"Error inserting data into MongoDB collection '{collection_name}' in database for repo '{repo_path}': {str(e)}")
            return False
            
    async def insert_to_mongodb_async(self, repo_path: str, collection_name: str, data: List[Dict[str, Any]]) -> bool:
        """
        Asynchronous version of MongoDB insertion
        Runs the synchronous method in a thread pool to prevent blocking
        """
        if not data or not collection_name or not isinstance(collection_name, str):
            print(f"Invalid parameters for MongoDB insertion: collection={collection_name}, data_length={len(data) if data else 0}")
            return False
            
        try:
            # Run the synchronous database operation in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.insert_to_mongodb,
                repo_path,
                collection_name,
                data
            )
            return result
        except Exception as e:
            print(f"Async error inserting data into MongoDB for {collection_name}: {str(e)}")
            return False

    async def batch_process_schemas(self, endpoints: List[Dict[str, Any]], repo_path: str) -> List[Dict[str, Any]]:
        """
        Process multiple endpoints' schemas in parallel
        """
        tasks = []
        for endpoint in endpoints:
            task = self._process_single_endpoint(endpoint, repo_path)
            tasks.append(task)
        
        # Execute all tasks concurrently and return results
        return await asyncio.gather(*tasks)
        
    async def _process_single_endpoint(self, endpoint: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """
        Process a single endpoint schema and mock data
        Helper method for batch processing
        """
        # Analyze schema
        schema = await self.analyze_endpoint_schema(endpoint)
        
        # Generate mock data if schema analysis was successful
        if schema and not schema.get("error"):
            mock_data_response = await self.generate_mock_data(schema)
            mock_data = mock_data_response.get("data", [])
            
            # Insert mock data if available
            if mock_data:
                collection_name = schema.get("collection_name", "unknown_collection")
                await self.insert_to_mongodb_async(repo_path, collection_name, mock_data)
        
        # Return updated endpoint
        return {**endpoint, "schema_analysis": schema}