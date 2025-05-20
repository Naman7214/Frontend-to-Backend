import json
import os

from fastapi import Depends

from src.app.prompts.postman_collection_llm_prompts import (
    POSTMAN_COLLECTION_SYSTEM_PROMPT,
    POSTMAN_COLLECTION_USER_PROMPT,
)
from src.app.services.anthropic_service import AnthropicService
from src.app.utils.response_parser import parse_response


class PostmanCollectionUsecase:
    def __init__(
        self,
        anthropic_service: AnthropicService = Depends(AnthropicService),
    ):
        self.anthropic_service = anthropic_service

    async def filter_json_by_paths(self, input_file_path: str):
        # Check if the input file exists
        if not os.path.exists(input_file_path):
            print(f"Error: Input file '{input_file_path}' not found.")
            return False

        try:
            # Read the input JSON file
            with open(input_file_path, "r") as f:
                data = json.load(f)

            # Filter for paths that match src/models/* and src/routes/*
            filtered_data = []
            for item in data:
                file_path = item.get("file_path", "")
                if file_path.startswith("src/models/") or file_path.startswith(
                    "src/routes/"
                ):
                    filtered_data.append(item)

            print(
                f"Successfully created filtered_code with {len(filtered_data)} filtered entries."
            )
            return filtered_data

        except json.JSONDecodeError:
            print(f"Error: '{input_file_path}' is not a valid JSON file.")
            return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

    async def execute(self, file_path: str):
        filtered_data = await self.filter_json_by_paths(file_path)

        user_prompt = POSTMAN_COLLECTION_USER_PROMPT.format(
            filtered_data=filtered_data
        )
        response = await self.anthropic_service.completions(
            system_prompt=POSTMAN_COLLECTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        response = parse_response(response)

        # Get the directory of the input file
        input_dir = os.path.dirname(file_path)

        # # Create the output file path in the same directory with name "postman_collection.json"
        output_file_path = os.path.join(input_dir, "postman_collection.json")

        with open(output_file_path, "w") as f:
            json.dump(response["postman_collection"], f, indent=4)

        return response["postman_collection"]
