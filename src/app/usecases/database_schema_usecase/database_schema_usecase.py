import asyncio
import json
import os
from typing import Any, Dict

from fastapi import Depends, HTTPException

from src.app.usecases.database_schema_usecase.helper import DatabaseSchemaHelper


class DatabaseSchemaUseCase:
    def __init__(self, helper: DatabaseSchemaHelper = Depends()):
        self.helper = helper

    async def execute(
        self, json_file_path: str, repo_path: str
    ) -> Dict[str, Any]:
        try:
            # Process the JSON file
            result = await self._process_json_file(json_file_path, repo_path)
            return result
        except Exception as e:
            print(
                f"Error in DatabaseSchemaUseCase execute for {json_file_path}, repo_path {repo_path}: {str(e)}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process schema analysis: {str(e)}",
            )

    async def _process_json_file(
        self, json_file_path: str, repo_path: str
    ) -> Dict[str, Any]:
        try:
            # Read the input JSON file
            with open(json_file_path, "r") as file:
                endpoints_data = json.load(file)

            # Process all endpoints concurrently
            schema_tasks = []
            for endpoint in endpoints_data.get("endpoints", []):
                # Create tasks for schema analysis
                task = self._process_endpoint(endpoint, repo_path)
                schema_tasks.append(task)

            # Wait for all schema analysis tasks to complete
            processed_endpoints = await asyncio.gather(*schema_tasks)

            endpoints_data["endpoints"] = processed_endpoints

            # Get the output directory and base filename
            output_dir = os.path.dirname(json_file_path)
            base_filename = os.path.splitext(os.path.basename(json_file_path))[
                0
            ]

            # Create output paths
            output_file = os.path.join(output_dir, f"{base_filename}.json")

            # Save the updated JSON with schema info
            with open(output_file, "w") as file:
                json.dump(endpoints_data, file, indent=2)

            print(
                f"Updated JSON with schema analysis and mock data status saved to {output_file}"
            )

            return endpoints_data

        except FileNotFoundError:
            print(f"File not found: {json_file_path}")
            raise HTTPException(
                status_code=404,
                detail=f"Input file not found: {json_file_path}",
            )
        except json.JSONDecodeError:
            print(f"Invalid JSON format in file: {json_file_path}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON format in {json_file_path}",
            )
        except Exception as e:
            print(f"Error processing file {json_file_path}: {str(e)}")
            return {
                "error": f"An unexpected error occurred: {str(e)}",
                "file_path": json_file_path,
            }

    async def _process_endpoint(
        self, endpoint: Dict[str, Any], repo_path: str
    ) -> Dict[str, Any]:
        """Process a single endpoint: analyze schema and generate/insert mock data"""
        # Analyze the endpoint to identify the schema
        schema_analysis = await self.helper.analyze_endpoint_schema(endpoint)

        # Create a copy of schema_analysis without samples for storing in the endpoint
        schema_analysis_for_json = {
            key: value
            for key, value in schema_analysis.items()
            if key != "samples"
        }

        db_name = os.path.basename(repo_path.rstrip("/"))

        # Update endpoint data with cleaned schema analysis (without samples)
        endpoint["database_schema"] = schema_analysis_for_json
        endpoint["database_schema"]["db_name"] = db_name

        # If schema analysis was successful, generate and insert mock data
        if schema_analysis and not schema_analysis.get("error"):
            collection_name = schema_analysis.get(
                "collection_name", "unknown_collection"
            )

            # Generate mock data using the original schema_analysis with samples
            mock_data_response = await self.helper.generate_mock_data(
                schema_analysis, num_records=10
            )
            mock_data_list = mock_data_response.get("data", [])

            if mock_data_list:
                # Insert mock data into MongoDB
                insertion_success = await self.helper.insert_to_mongodb_async(
                    repo_path, collection_name, mock_data_list
                )
                if insertion_success:
                    print(f"Mock data inserted for {collection_name}")
                else:
                    print(f"Mock data insertion failed for {collection_name}")
            else:
                print(f"No mock data generated for {collection_name}")
        else:
            print(
                f"Skipping mock data generation for endpoint {endpoint.get('endpointName')} due to schema analysis error or empty result."
            )

        return endpoint
