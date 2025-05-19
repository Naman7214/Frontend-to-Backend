import asyncio
import json
import re
import traceback
from typing import Any, Dict, List

from fastapi import Depends, HTTPException

from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.prompts.database_schema_prompt import (
    DATABASE_SCHEMA_SYSTEM_PROMPT,
    DATABASE_SCHEMA_USER_PROMPT,
)
from src.app.repositories.database_schema_repo import DatabaseRepository
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.api_service import ApiService
from src.app.services.openai_service import OpenAIService


class DatabaseSchemaHelper:
    def __init__(
        self,
        openai_client: OpenAIService = Depends(),
        db_repo: DatabaseRepository = Depends(),
        api_service: ApiService = Depends(),
        error_repo: ErrorRepo = Depends(),
    ):
        self.openai_client = openai_client
        # self.model = settings.OPENAI_MODEL
        self.database_schema_user_prompt = DATABASE_SCHEMA_USER_PROMPT
        self.database_schema_system_prompt = DATABASE_SCHEMA_SYSTEM_PROMPT
        self.mock_data_api_url = settings.MOCK_DATA_API_URL
        self.api_service = api_service
        self.db_repo = db_repo
        self.error_repo = error_repo
        # Semaphore to limit concurrent API calls if needed
        self.semaphore = asyncio.Semaphore(
            10
        )  # Adjust number based on API limits

    def extract_schema_info(
        self, endpoint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract schema information from endpoint data.
        """
        try:
            return {
                "collection_name": endpoint_data.get(
                    "collection_name", "unknown"
                ),
                "schema": endpoint_data.get("schema", {}),
                "samples": endpoint_data.get("samples", {}),
            }
        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Error in DatabaseSchemaHelper.extract_schema_info: Unable to extract schema information. Error: {str(e)}. Trace: {stack_trace}"
            # We can't await in a synchronous method, so we'll handle this in the caller
            return {
                "error": True,
                "error_message": f"Failed to extract schema information: {str(e)}",
                "collection_name": "unknown",
                "schema": {},
                "samples": {},
            }

    async def analyze_endpoint_schema(
        self, endpoint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze endpoint schema using OpenAI"""
        endpoint_name = endpoint_data.get("endpointName", "Unknown")

        async with self.semaphore:  # Limit concurrent API calls
            try:
                user_prompt = self.database_schema_user_prompt.format(
                    endpointName=endpoint_data["endpointName"],
                    method=endpoint_data["method"],
                    description=endpoint_data["description"],
                    payload=json.dumps(endpoint_data["payload"], indent=2),
                    response=json.dumps(endpoint_data["response"], indent=2),
                )

                content = await self.openai_client.completions(
                    user_prompt=user_prompt,
                    system_prompt=self.database_schema_system_prompt,
                    temperature=0.5,
                )

                json_match = re.search(r"{.*}", content, re.DOTALL)
                if json_match:
                    schema_json_str = json_match.group(0)
                else:
                    error_msg = f"Error in DatabaseSchemaHelper.analyze_endpoint_schema: No JSON content found in OpenAI response for endpoint {endpoint_name}"
                    await self._log_error(error_msg)
                    return {
                        "error": True,
                        "error_message": "No JSON content found in OpenAI response",
                        "collection_name": "unknown",
                        "schema": {},
                        "samples": {},
                    }

                try:
                    schema_json = json.loads(schema_json_str.strip())
                    return schema_json
                except json.JSONDecodeError as je:
                    error_msg = f"Error in DatabaseSchemaHelper.analyze_endpoint_schema: Invalid JSON format in OpenAI response for endpoint {endpoint_name}. Error: {str(je)}"
                    await self._log_error(error_msg)
                    return {
                        "error": True,
                        "error_message": f"Invalid JSON format in OpenAI response: {str(je)}",
                        "collection_name": "unknown",
                        "schema": {},
                        "samples": {},
                    }

            except Exception as e:
                stack_trace = traceback.format_exc()
                error_msg = f"Error in DatabaseSchemaHelper.analyze_endpoint_schema for endpoint {endpoint_name}: {str(e)}. Trace: {stack_trace}"
                await self._log_error(error_msg)
                return {
                    "error": True,
                    "error_message": f"Schema analysis failed: {str(e)}",
                    "collection_name": "unknown",
                    "schema": {},
                    "samples": {},
                }

    async def generate_mock_data(
        self, schema_info: Dict[str, Any], num_records: int = 10
    ) -> Dict[str, Any]:
        """
        Call external API to generate mock data based on the schema.
        """
        collection_name = schema_info.get("collection_name", "unknown")

        async with self.semaphore:  # Limit concurrent API calls
            try:
                # Add await and expect direct JSON response or exception
                mock_data = await self.api_service.post(
                    url=self.mock_data_api_url,
                    data=schema_info.get("samples", {}),
                )

                if not mock_data or not mock_data.get("data"):
                    error_msg = f"Error in DatabaseSchemaHelper.generate_mock_data: No mock data returned from API for collection {collection_name}"
                    await self._log_error(error_msg)
                    return {
                        "data": [],
                        "error": "No mock data returned from API",
                    }

                return mock_data

            except HTTPException as he:
                error_msg = f"Error in DatabaseSchemaHelper.generate_mock_data: HTTP error while generating mock data for {collection_name}. Status: {he.status_code}, Detail: {he.detail}"
                await self._log_error(error_msg)
                return {"data": [], "error": f"HTTP error: {he.detail}"}

            except Exception as e:
                stack_trace = traceback.format_exc()
                error_msg = f"Error in DatabaseSchemaHelper.generate_mock_data for collection {collection_name}: {str(e)}. Trace: {stack_trace}"
                await self._log_error(error_msg)
                return {"data": [], "error": str(e)}

    def insert_to_mongodb(
        self, repo_path: str, collection_name: str, data: List[Dict[str, Any]]
    ) -> bool:
        """
        Synchronous version of MongoDB insertion (kept for backward compatibility)
        """
        if self.db_repo is None:
            error_msg = "DatabaseSchemaHelper.insert_to_mongodb: DatabaseRepository instance not available. Skipping database insertion."
            # Can't await in a synchronous method
            return False

        if not data:
            error_msg = f"DatabaseSchemaHelper.insert_to_mongodb: No data provided to insert into collection {collection_name}"
            # Can't await in a synchronous method
            return False

        if not collection_name or not isinstance(collection_name, str):
            error_msg = f"DatabaseSchemaHelper.insert_to_mongodb: Invalid collection name: {collection_name}. Skipping insertion."
            # Can't await in a synchronous method
            return False

        try:
            db = self.db_repo.initialize_db_from_repo_path(repo_path)
            if db is None:
                error_msg = f"DatabaseSchemaHelper.insert_to_mongodb: Failed to initialize database using repo path '{repo_path}'. Skipping insertion."
                # Can't await in a synchronous method
                return False

            if collection_name in db.list_collection_names():
                db[collection_name].drop()

            collection = self.db_repo.create_collection(db, collection_name)
            inserted_ids = self.db_repo.insert_many(collection, data)
            return True

        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Error in DatabaseSchemaHelper.insert_to_mongodb for collection '{collection_name}' in database for repo '{repo_path}': {str(e)}. Trace: {stack_trace}"
            # Can't await in a synchronous method
            return False

    async def insert_to_mongodb_async(
        self, repo_path: str, collection_name: str, data: List[Dict[str, Any]]
    ) -> bool:
        """
        Asynchronous version of MongoDB insertion
        Runs the synchronous method in a thread pool to prevent blocking
        """
        if (
            not data
            or not collection_name
            or not isinstance(collection_name, str)
        ):
            error_msg = f"Error in DatabaseSchemaHelper.insert_to_mongodb_async: Invalid parameters for MongoDB insertion: collection={collection_name}, data_length={len(data) if data else 0}"
            await self._log_error(error_msg)
            return False

        try:
            # Run the synchronous database operation in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self.insert_to_mongodb, repo_path, collection_name, data
            )
            return result
        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Error in DatabaseSchemaHelper.insert_to_mongodb_async for collection '{collection_name}' in repo '{repo_path}': {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            return False

    async def batch_process_schemas(
        self, endpoints: List[Dict[str, Any]], repo_path: str
    ) -> List[Dict[str, Any]]:
        """
        Process multiple endpoints' schemas in parallel
        """
        if not endpoints or not isinstance(endpoints, list):
            error_msg = f"Error in DatabaseSchemaHelper.batch_process_schemas: Invalid endpoints data provided. Expected list, got {type(endpoints)}"
            await self._log_error(error_msg)
            return []

        try:
            tasks = []
            for endpoint in endpoints:
                task = self._process_single_endpoint(endpoint, repo_path)
                tasks.append(task)

            # Execute all tasks concurrently and return results
            return await asyncio.gather(*tasks)
        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Error in DatabaseSchemaHelper.batch_process_schemas for repo_path '{repo_path}': {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            return []

    async def _process_single_endpoint(
        self, endpoint: Dict[str, Any], repo_path: str
    ) -> Dict[str, Any]:
        """
        Process a single endpoint schema and mock data
        Helper method for batch processing
        """
        endpoint_name = endpoint.get("endpointName", "unknown_endpoint")

        try:
            # Analyze schema
            schema = await self.analyze_endpoint_schema(endpoint)

            # Generate mock data if schema analysis was successful
            if schema and not schema.get("error"):
                mock_data_response = await self.generate_mock_data(schema)
                mock_data = mock_data_response.get("data", [])

                # Insert mock data if available
                if mock_data:
                    collection_name = schema.get(
                        "collection_name", "unknown_collection"
                    )
                    result = await self.insert_to_mongodb_async(
                        repo_path, collection_name, mock_data
                    )
                    if not result:
                        error_msg = f"Error in DatabaseSchemaHelper._process_single_endpoint: Failed to insert mock data for endpoint {endpoint_name}, collection {collection_name}"
                        await self._log_error(error_msg)
                        schema["insertion_error"] = "Failed to insert mock data"
                else:
                    error_msg = f"Error in DatabaseSchemaHelper._process_single_endpoint: No mock data generated for endpoint {endpoint_name}"
                    await self._log_error(error_msg)
                    schema["mock_data_error"] = "No mock data generated"

            # Return updated endpoint
            return {**endpoint, "schema_analysis": schema}
        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Error in DatabaseSchemaHelper._process_single_endpoint for endpoint {endpoint_name}, repo_path {repo_path}: {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            return {
                **endpoint,
                "schema_analysis": {
                    "error": True,
                    "error_message": f"Failed to process endpoint: {str(e)}",
                    "collection_name": "unknown",
                    "schema": {},
                    "samples": {},
                },
            }

    async def _log_error(self, error_message: str) -> None:
        """Log error to MongoDB using ErrorRepo"""
        try:
            error = Error(error_message=error_message)
            await self.error_repo.insert_error(error)
        except Exception as e:
            # If logging to MongoDB fails, we don't want to throw another exception
            # This would be handled by the monitoring system in production
            pass
