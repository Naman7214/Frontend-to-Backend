import json
import os

from fastapi import Depends

from src.app.prompts.set_priority_prompts import (
    SET_PRIORITY_SYSTEM_PROMPT,
    SET_PRIORITY_USER_PROMPT,
)
from src.app.services.openai_service import OpenAIService
from src.app.utils.response_parser import parse_response
from src.app.utils.store_response import store_json_response


class SetPriorityUseCase:

    def __init__(self, openai_service: OpenAIService = Depends(OpenAIService)):
        self.openai_service = openai_service

    async def set_priority(self, json_file_path: str):
        with open(json_file_path, "r") as file:
            data = json.load(file)
        user_prompts = SET_PRIORITY_USER_PROMPT.format(context=data)
        response = await self.openai_service.completions(
            user_prompt=user_prompts,
            system_prompt=SET_PRIORITY_SYSTEM_PROMPT,
        )
        parsed_response = parse_response(response)
        # Extract the directory path from the input file
        input_dir = os.path.dirname(json_file_path)

        # Create a new file name based on the original file
        base_name = os.path.basename(json_file_path)
        new_file_name = f"priority_end_points.json"
        output_path = os.path.join(input_dir, new_file_name)

        params = {
            "response": parsed_response,
            "file_path": output_path,
        }
        await store_json_response(params)

        # Sort the original JSON file content based on the prioritized endpoints
        sorted_data = self.sort_endpoints_based_on_priority(
            data, parsed_response
        )

        # Save the sorted data to a new file
        sorted_file_name = f"sorted_endpoints.json"
        sorted_output_path = os.path.join(input_dir, sorted_file_name)
        with open(sorted_output_path, "w") as file:
            json.dump(sorted_data, file, indent=4)

        print(f"Sorted endpoints saved to: {sorted_output_path}")

        return sorted_data

    def sort_endpoints_based_on_priority(self, original_data, priority_data):
        """
        Sort the original endpoints data based on the priority order defined in priority_data.

        Args:
            original_data: The original JSON data containing endpoints
            priority_data: The prioritized endpoints data

        Returns:
            A new sorted list of endpoints
        """
        # Handle the case where priority_data is a list of endpoints directly
        if isinstance(priority_data, list):
            endpoints_list = priority_data
        # Handle the case where priority_data has an "end_points" key containing the list
        elif isinstance(priority_data, dict) and "end_points" in priority_data:
            endpoints_list = priority_data["end_points"]
        else:
            print(
                "Warning: Unexpected priority data format. Returning original data."
            )
            return original_data

        # Create a mapping of endpoint name+method to its priority order
        priority_map = {}

        for i, endpoint in enumerate(endpoints_list):
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
                print(f"Warning: Unexpected endpoint format: {endpoint}")

        # Define a sorting function for endpoints in original data
        def get_priority(endpoint):
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

        # Sort the original data based on priorities
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
                # If structure is different, return as is with a warning
                print(
                    "Warning: Could not sort endpoints - unexpected data structure"
                )
                sorted_data = original_data

        return sorted_data
