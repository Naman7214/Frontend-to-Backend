#!/usr/bin/env python3
# filepath: json_schema_analyzer_usecase.py

import json
import os
# Removed logging import
from typing import Dict, List, Any
from fastapi import Depends, HTTPException
from src.app.usecases.database_schema_usecase.helper import DatabaseSchemaHelper
from src.app.utils.store_response import store_json_response

class DatabaseSchemaUseCase:    
    def __init__(self, helper: DatabaseSchemaHelper = Depends()):
        self.helper = helper

    async def execute(self, json_file_path: str, repo_path: str) -> Dict[str, Any]: # Added repo_path
        try:
            # Process the JSON file
            result = await self._process_json_file(json_file_path, repo_path) # Pass repo_path
            return result
        except Exception as e:
            # Added repo_path to log message
            print(f"Error in DatabaseSchemaUseCase execute for {json_file_path}, repo_path {repo_path}: {str(e)}") 
            raise HTTPException(status_code=500, detail=f"Failed to process schema analysis: {str(e)}")
    
    async def _process_json_file(self, json_file_path: str, repo_path: str) -> Dict[str, Any]: # Added repo_path
        try:
            # Read the input JSON file
            with open(json_file_path, 'r') as file:
                endpoints_data = json.load(file)
            
            processed_endpoints = []
            # Process each endpoint
            for endpoint in endpoints_data.get('endpoints', []):
                # Analyze the endpoint to identify the schema
                schema_analysis = await self.helper.analyze_endpoint_schema(endpoint)
                
                 # Create a copy of schema_analysis without samples for storing in the endpoint
                schema_analysis_for_json = {key: value for key, value in schema_analysis.items() if key != 'samples'}

                db_name = os.path.basename(repo_path.rstrip('/'))

                # Update endpoint data with cleaned schema analysis (without samples)
                endpoint['database_schema'] = schema_analysis_for_json
                endpoint['database_schema']['db_name'] = db_name
                
                # If schema analysis was successful, generate and insert mock data
                # (Use the original schema_analysis with samples for this)
                if schema_analysis and not schema_analysis.get("error"):
                    collection_name = schema_analysis.get("collection_name", "unknown_collection")
                    
                    # Generate mock data using the original schema_analysis with samples
                    mock_data_response = await self.helper.generate_mock_data(schema_analysis, num_records=10)
                    mock_data_list = mock_data_response.get("data", [])

                    if mock_data_list:
                        # Insert mock data into MongoDB, passing repo_path
                        insertion_success = self.helper.insert_to_mongodb(repo_path, collection_name, mock_data_list)
                        if insertion_success:
                             print(f"Mock data inserted for {collection_name}") # Replaced logging
                        else:
                            print(f"Mock data insertion failed for {collection_name}") # Replaced logging
                    else:
                        print(f"No mock data generated for {collection_name}") # Replaced logging
                else:
                    print(f"Skipping mock data generation for endpoint {endpoint.get('endpointName')} due to schema analysis error or empty result.") # Replaced logging
                processed_endpoints.append(endpoint)
            
            endpoints_data['endpoints'] = processed_endpoints

            # Get the output directory and base filename
            output_dir = os.path.dirname(json_file_path)
            base_filename = os.path.splitext(os.path.basename(json_file_path))[0]
            
            # Create output paths
            output_file = os.path.join(output_dir, f'{base_filename}.json')
            
            # Save the updated JSON with schema info
            with open(output_file, 'w') as file:
                json.dump(endpoints_data, file, indent=2)
            
            print(f"Updated JSON with schema analysis and mock data status saved to {output_file}") # Replaced logging
            
            return endpoints_data
            
        except FileNotFoundError:
            print(f"File not found: {json_file_path}") # Replaced logging
            raise HTTPException(status_code=404, detail=f"Input file not found: {json_file_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON format in file: {json_file_path}") # Replaced logging
            raise HTTPException(status_code=400, detail=f"Invalid JSON format in {json_file_path}")
        except Exception as e:
            print(f"Error processing file {json_file_path}: {str(e)}") # Replaced logging
            # Return a more structured error if preferred, or re-raise as HTTPException
            return {"error": f"An unexpected error occurred: {str(e)}", "file_path": json_file_path}

