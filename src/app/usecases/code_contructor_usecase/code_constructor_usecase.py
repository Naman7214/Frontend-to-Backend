import json
import os
import shutil
import traceback
import zipfile
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class CodeConstructorUseCase:
    def __init__(
        self,
        error_repo: ErrorRepo = Depends()
    ):
        self.error_repo = error_repo

    async def execute(self, code_json_path: str) -> str:
        """
        Reads JSON file containing code structure and creates the directory structure with files,
        then zips the entire directory.

        Args:
            code_json_path (str): Path to the JSON file containing code structure

        Returns:
            str: Path to the created ZIP file containing the api directory
            
        Raises:
            HTTPException: If any step in the process fails
        """
        try:
            # Validate input
            if not code_json_path or not isinstance(code_json_path, str):
                error_msg = f"Error in CodeConstructorUseCase.execute: Invalid JSON path provided: {code_json_path}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=400, detail="Invalid JSON path provided")
                
            if not os.path.exists(code_json_path):
                error_msg = f"Error in CodeConstructorUseCase.execute: JSON file not found: {code_json_path}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=404, detail=f"JSON file not found: {code_json_path}")
            
            # Get directory where the JSON file is located
            json_dir = os.path.dirname(code_json_path)

            # Create api directory in the same folder as the JSON
            api_dir = os.path.join(json_dir, "api")

            try:
                # If the api directory already exists, remove it to start fresh
                if os.path.exists(api_dir):
                    shutil.rmtree(api_dir)
            except Exception as e:
                error_msg = f"Error in CodeConstructorUseCase.execute: Failed to remove existing api directory: {api_dir}. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=500, detail=f"Failed to remove existing api directory: {str(e)}")

            try:
                # Create the api directory
                os.makedirs(api_dir)
            except Exception as e:
                error_msg = f"Error in CodeConstructorUseCase.execute: Failed to create api directory: {api_dir}. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=500, detail=f"Failed to create api directory: {str(e)}")

            # Read the JSON file
            try:
                with open(code_json_path, "r") as file:
                    files_data = json.load(file)
                    
                if not isinstance(files_data, list):
                    error_msg = f"Error in CodeConstructorUseCase.execute: Invalid JSON format in {code_json_path}. Expected a list of file objects."
                    await self._log_error(error_msg)
                    raise HTTPException(status_code=400, detail="Invalid JSON format. Expected a list of file objects.")
            except json.JSONDecodeError as je:
                error_msg = f"Error in CodeConstructorUseCase.execute: Invalid JSON format in {code_json_path}. Error: {str(je)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(je)}")
            except Exception as e:
                error_msg = f"Error in CodeConstructorUseCase.execute: Failed to read JSON file: {code_json_path}. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=500, detail=f"Failed to read JSON file: {str(e)}")

            # Create each file and its parent directories
            file_count = 0
            try:
                for file_info in files_data:
                    file_path = file_info.get("file_path")
                    code = file_info.get("code")

                    # Skip if either is missing
                    if not file_path or code is None:
                        continue

                    # Create the full path for the file
                    full_path = os.path.join(api_dir, file_path)

                    # Create parent directories if they don't exist
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    # Write the file content
                    with open(full_path, "w") as f:
                        f.write(code)
                        
                    file_count += 1
                
                if file_count == 0:
                    error_msg = f"Error in CodeConstructorUseCase.execute: No valid files found in JSON: {code_json_path}"
                    await self._log_error(error_msg)
                    raise HTTPException(status_code=400, detail="No valid files found in JSON")
            except Exception as e:
                error_msg = f"Error in CodeConstructorUseCase.execute: Failed to create code files. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=500, detail=f"Failed to create code files: {str(e)}")

            # Create ZIP file of the api directory
            zip_path = os.path.join(json_dir, "api.zip")

            try:
                # Remove existing zip file if it exists
                if os.path.exists(zip_path):
                    os.remove(zip_path)

                # Create the zip file
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    # Walk through all files and directories in the api directory
                    for root, dirs, files in os.walk(api_dir):
                        for file in files:
                            # Get the full path of the file
                            file_path = os.path.join(root, file)
                            # Get the relative path to include in the zip
                            rel_path = os.path.relpath(
                                file_path, os.path.dirname(api_dir)
                            )
                            # Add the file to the zip
                            zipf.write(file_path, rel_path)

                    # Check if postman_collection.json exists and add it to the zip
                    postman_collection_path = os.path.join(
                        json_dir, "postman_collection.json"
                    )
                    if os.path.exists(postman_collection_path):
                        # Add the postman collection to the root of the zip
                        zipf.write(postman_collection_path, "postman_collection.json")
                
                # Verify the zip file was created
                if not os.path.exists(zip_path):
                    error_msg = f"Error in CodeConstructorUseCase.execute: Failed to create zip file: {zip_path}"
                    await self._log_error(error_msg)
                    raise HTTPException(status_code=500, detail="Failed to create zip file")
            except Exception as e:
                error_msg = f"Error in CodeConstructorUseCase.execute: Failed to create zip file: {zip_path}. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(status_code=500, detail=f"Failed to create zip file: {str(e)}")

            return zip_path
            
        except HTTPException:
            # Re-raise HTTPExceptions as they're already formatted properly
            raise
        except Exception as e:
            # Handle any unexpected exceptions
            stack_trace = traceback.format_exc()
            error_msg = f"Unexpected error in CodeConstructorUseCase.execute for file: {code_json_path}. Error: {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def _log_error(self, error_message: str) -> None:
        """Log error to MongoDB using ErrorRepo"""
        try:
            error = Error(error_message=error_message)
            await self.error_repo.insert_error(error)
        except Exception as e:
            # If logging to MongoDB fails, we don't want to throw another exception
            # This would be handled by the monitoring system in production
            pass
