import json
import os
import traceback
from typing import Dict, List, Union

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.prompts.set_priority_prompts import (
    SET_PRIORITY_SYSTEM_PROMPT,
    SET_PRIORITY_USER_PROMPT,
)
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.openai_service import OpenAIService
from src.app.utils.response_parser import parse_response
from src.app.utils.store_response import store_json_response


class SetPriorityUseCase:

    def __init__(
        self,
        openai_service: OpenAIService = Depends(OpenAIService),
        error_repo: ErrorRepo = Depends(),
    ):
        self.openai_service = openai_service
        self.error_repo = error_repo

    async def set_priority(self, json_file_path: str):
        try:
            # Validate the input file path
            if not os.path.exists(json_file_path):
                error_msg = f"Error in SetPriorityUseCase.set_priority: File not found: {json_file_path}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=404, detail=f"File not found: {json_file_path}"
                )

            try:
                with open(json_file_path, "r") as file:
                    data = json.load(file)
            except json.JSONDecodeError as je:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Invalid JSON format in file {json_file_path}. Error: {str(je)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON format in file: {json_file_path}",
                )
            except IOError as ioe:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Failed to read file {json_file_path}. Error: {str(ioe)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read file: {json_file_path}",
                )

            # Generate OpenAI completion
            try:
                user_prompts = SET_PRIORITY_USER_PROMPT.format(context=data)
                response = await self.openai_service.completions(
                    user_prompt=user_prompts,
                    system_prompt=SET_PRIORITY_SYSTEM_PROMPT,
                )
            except Exception as oe:
                error_msg = f"Error in SetPriorityUseCase.set_priority: OpenAI API error for file {json_file_path}. Error: {str(oe)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate priorities using AI: {str(oe)}",
                )

            # Parse the response
            try:
                parsed_response = parse_response(response)
            except Exception as pe:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Failed to parse OpenAI response for file {json_file_path}. Error: {str(pe)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse AI response: {str(pe)}",
                )

            # Extract the directory path from the input file
            input_dir = os.path.dirname(json_file_path)

            # Create output paths
            new_file_name = f"priority_end_points.json"
            output_path = os.path.join(input_dir, new_file_name)

            # Store priority response
            try:
                params = {
                    "response": parsed_response,
                    "file_path": output_path,
                }
                await store_json_response(params)
            except Exception as se:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Failed to store priority response for file {json_file_path}. Error: {str(se)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store priority response: {str(se)}",
                )

            # Sort the original JSON file content based on the prioritized endpoints
            try:
                sorted_data = self.sort_endpoints_based_on_priority(
                    data, parsed_response
                )
            except Exception as sse:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Failed to sort endpoints based on priority for file {json_file_path}. Error: {str(sse)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to sort endpoints: {str(sse)}",
                )

            # Save the sorted data to a new file
            try:
                sorted_file_name = f"sorted_endpoints.json"
                sorted_output_path = os.path.join(input_dir, sorted_file_name)
                with open(sorted_output_path, "w") as file:
                    json.dump(sorted_data, file, indent=4)
            except Exception as we:
                error_msg = f"Error in SetPriorityUseCase.set_priority: Failed to write sorted endpoints to file {sorted_output_path}. Error: {str(we)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to write sorted endpoints to file: {str(we)}",
                )

            return sorted_data

        except HTTPException:
            # Re-raise HTTPExceptions as they're already formatted properly
            raise
        except Exception as e:
            # Handle any unexpected exceptions
            stack_trace = traceback.format_exc()
            error_msg = f"Unexpected error in SetPriorityUseCase.set_priority for file {json_file_path}. Error: {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}",
            )

    def sort_endpoints_based_on_priority(
        self, original_data: Union[List, Dict], priority_data: Union[List, Dict]
    ) -> Union[List, Dict]:
        """
        Sort the original endpoints data based on the priority order defined in priority_data.

        Args:
            original_data: The original JSON data containing endpoints
            priority_data: The prioritized endpoints data

        Returns:
            A new sorted list of endpoints
        """
        try:
            # Input validation
            if not original_data:
                error_msg = "Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Original data is empty"
                # Can't await in a synchronous method
                return original_data

            if not priority_data:
                error_msg = "Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Priority data is empty"
                # Can't await in a synchronous method
                return original_data

            # Handle the case where priority_data is a list of endpoints directly
            if isinstance(priority_data, list):
                endpoints_list = priority_data
            # Handle the case where priority_data has an "end_points" key containing the list
            elif (
                isinstance(priority_data, dict)
                and "end_points" in priority_data
            ):
                endpoints_list = priority_data["end_points"]
            else:
                error_msg = f"Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Unexpected priority data format: {type(priority_data)}"
                # Can't await in a synchronous method
                return original_data

            # Create a mapping of endpoint name+method to its priority order
            priority_map = {}

            for i, endpoint in enumerate(endpoints_list):
                try:
                    # Check if endpoint is a dictionary with the expected keys
                    if isinstance(endpoint, dict):
                        endpoint_name = endpoint.get("endpoint_name", "")
                        method = endpoint.get("method", "")
                        # Create a unique key based on endpoint_name and method
                        key = f"{endpoint_name}_{method}"
                        priority_map[key] = i
                    elif isinstance(endpoint, str):
                        # Handle case where endpoint is just a string
                        priority_map[endpoint] = i
                    else:
                        error_msg = f"Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Unexpected endpoint format: {type(endpoint)}"
                        # Skip this endpoint but continue processing others
                except Exception as inner_e:
                    # Skip this endpoint but continue processing others
                    error_msg = f"Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Failed to process endpoint at index {i}. Error: {str(inner_e)}"
                    # Can't await in a synchronous method
                    continue

            # Define a sorting function for endpoints in original data
            def get_priority(endpoint):
                try:
                    if isinstance(endpoint, dict):
                        # Try to match using endpointName or endpoint_name
                        endpoint_name = endpoint.get(
                            "endpointName", endpoint.get("endpoint_name", "")
                        )
                        method = endpoint.get("method", "")
                        key = f"{endpoint_name}_{method}"
                        return priority_map.get(key, float("inf"))
                    else:
                        # If endpoint is not a dict, try using it directly as a key
                        return priority_map.get(str(endpoint), float("inf"))
                except Exception as inner_e:
                    # If there's an error, assign lowest priority
                    error_msg = f"Error in get_priority function: Failed to get priority for endpoint. Error: {str(inner_e)}"
                    # Can't await in a nested function
                    return float("inf")

            # Sort the original data based on priorities
            try:
                if isinstance(original_data, list):
                    sorted_data = sorted(original_data, key=get_priority)
                else:
                    # If original_data is not a list (e.g., dictionary with 'endpoints' key)
                    # Extract the endpoints list and sort it
                    if "endpoints" in original_data:
                        original_data["endpoints"] = sorted(
                            original_data["endpoints"], key=get_priority
                        )
                        sorted_data = original_data
                    else:
                        # If structure is different, return as is
                        error_msg = "Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Could not sort endpoints - unexpected data structure"
                        # Can't await in a synchronous method
                        sorted_data = original_data

                return sorted_data
            except Exception as sort_e:
                # If sorting fails, return the original data
                error_msg = f"Error in SetPriorityUseCase.sort_endpoints_based_on_priority: Sorting failed. Error: {str(sort_e)}"
                # Can't await in a synchronous method
                return original_data

        except Exception as e:
            # If there's an unexpected error, log it and return the original data
            stack_trace = traceback.format_exc()
            error_msg = f"Unexpected error in SetPriorityUseCase.sort_endpoints_based_on_priority: {str(e)}. Trace: {stack_trace}"
            # Can't await in a synchronous method
            return original_data

    async def _log_error(self, error_message: str) -> None:
        """Log error to MongoDB using ErrorRepo"""
        try:
            error = Error(error_message=error_message)
            await self.error_repo.insert_error(error)
        except Exception as e:
            # If logging to MongoDB fails, we don't want to throw another exception
            # This would be handled by the monitoring system in production
            pass
