import json
import os
import traceback
from typing import Any, Dict, Tuple, List

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.usecases.endpoint_usecase.helper import EndpointHelper


class EndpointUseCase:
    def __init__(
        self, 
        endpoint_helper: EndpointHelper = Depends(EndpointHelper),
        error_repo: ErrorRepo = Depends(ErrorRepo)
    ) -> None:
        self.endpoint_helper = endpoint_helper
        self.error_repo = error_repo

    async def execute(
        self,
        repo_path: str,
        output_path: str = None,
        verbose: bool = False,
        max_files: int = None,
        all_files: bool = False,
        api_files: bool = False,
        react_hooks: bool = False,
        auth_files: bool = False,
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Extract API endpoint specifications from a React codebase.

        Args:
            repo_path (str): Path to the React repository to analyze
            output_path (str, optional): Path to save JSON output. Defaults to None.
            verbose (bool, optional): Print verbose output during processing. Defaults to False.
            max_files (int, optional): Maximum number of files to analyze. Defaults to None (no limit).
            all_files (bool, optional): Analyze all JS/TS files. Defaults to False.
            api_files (bool, optional): Target API-related files. Defaults to False.
            react_hooks (bool, optional): Find files using React hooks. Defaults to False.
            auth_files (bool, optional): Find auth-related files. Defaults to False.

        Returns:
            Tuple[str, str, List[Dict[str, Any]]]: Tuple containing output_path, output_with_payload_sample_path, and simplified_endpoints
        """
        try:
            # Validate repo_path exists
            if not os.path.isdir(repo_path):
                raise ValueError(f"Repository path does not exist: {repo_path}")

            # Extract endpoints
            result = await self.endpoint_helper.extract_endpoints(
                root_dir=repo_path,
                verbose=verbose,
                max_files=max_files,
                all_files=all_files,
                api_files=api_files,
                react_hooks=react_hooks,
                auth_files=auth_files,
            )

            # Initialize variables with default values
            output_with_payload_sample_path = None
            simplified_endpoints = []

            # Save to output file if specified
            if output_path:
                try:
                    # Ensure the directory exists
                    os.makedirs(
                        os.path.dirname(os.path.abspath(output_path)), exist_ok=True
                    )

                    # Create path for sample payload file by removing .json extension if present
                    base_path = output_path
                    if base_path.endswith(".json"):
                        base_path = base_path[:-5]  # Remove .json extension
                    output_with_payload_sample_path = (
                        f"{base_path}_with_payload_sample.json"
                    )
                    os.makedirs(
                        os.path.dirname(
                            os.path.abspath(output_with_payload_sample_path)
                        ),
                        exist_ok=True,
                    )

                    # Write the JSON output
                    with open(output_with_payload_sample_path, "w") as f:
                        json.dump(result, f, indent=2)

                    output_path_result = []
                    for ele in result.get("endpoints", []):
                        temp = {}
                        for key, value in ele.items():
                            if key == "payload_sample":
                                continue
                            temp[key] = value
                        output_path_result.append(temp)

                    final_result = {"endpoints": output_path_result}
                    with open(output_path, "w") as f:
                        json.dump(final_result, f, indent=2)

                    if verbose:
                        print(f"Saved endpoints to {output_with_payload_sample_path}")
                        print(f"Saved endpoints to {output_path}")

                    # Add the output path to the result
                    result["output_path"] = output_path
                    simplified_endpoints = [
                        {
                            "endpointName": endpoint["endpointName"],
                            "method": endpoint["method"],
                            "description": endpoint["description"],
                        }
                        for endpoint in result.get("endpoints", [])
                    ]
                except (OSError, IOError) as file_ex:
                    # Handle file operation errors
                    error_message = f"File operation error in EndpointUseCase.execute when saving output: {str(file_ex)}"
                    error = Error(error_message)
                    await self.error_repo.insert_error(error)
                    
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to save endpoint analysis results: {str(file_ex)}"
                    )
                except Exception as output_ex:
                    # Handle any other errors during output saving
                    error_message = f"Error in EndpointUseCase.execute when processing output: {str(output_ex)}"
                    error = Error(error_message)
                    await self.error_repo.insert_error(error)
                    
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to process endpoint analysis results: {str(output_ex)}"
                    )

            return (
                output_path,
                output_with_payload_sample_path,
                simplified_endpoints,
            )
            
        except HTTPException as http_ex:
            # Log the error to MongoDB and re-raise
            error_message = f"HTTP Exception in EndpointUseCase.execute: {http_ex.detail} - Status code: {http_ex.status_code}"
            error = Error(error_message)
            await self.error_repo.insert_error(error)
            
            # Re-raise to be handled by the API layer
            raise
            
        except ValueError as val_ex:
            # Handle validation errors
            error_message = f"Validation error in EndpointUseCase.execute: {str(val_ex)}"
            error = Error(error_message)
            await self.error_repo.insert_error(error)
            
            # Convert to HTTP exception with appropriate status code
            raise HTTPException(status_code=400, detail=str(val_ex))
            
        except OSError as os_ex:
            # Handle file system errors
            error_message = f"File system error in EndpointUseCase.execute when accessing repo_path {repo_path}: {str(os_ex)}"
            error = Error(error_message)
            await self.error_repo.insert_error(error)
            
            raise HTTPException(
                status_code=500, 
                detail=f"File system operation failed on repository path: {str(os_ex)}"
            )
            
        except Exception as ex:
            # Get stack trace for detailed error logging
            stack_trace = traceback.format_exc()
            
            # Create a detailed error message
            error_message = (
                f"Unexpected error in EndpointUseCase.execute while processing repo_path {repo_path}: "
                f"{str(ex)}\nStack trace: {stack_trace}"
            )
            
            # Log the error to MongoDB
            error = Error(error_message)
            await self.error_repo.insert_error(error)
            
            # Raise a generic HTTP exception with a user-friendly message
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while analyzing repository endpoints."
            )
