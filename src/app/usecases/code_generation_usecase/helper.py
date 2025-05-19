import json
import os
import traceback
from typing import Any, Dict, List, Optional

from fastapi import Depends

from src.app.models.domain.error import Error
from src.app.prompts.code_generation_prompt import CODE_GENERATION_PROMPT
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.anthropic_service import AnthropicService
from src.app.utils.response_parser import parse_response
from src.app.utils.store_response import store_json_response

TEMPLATE_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
    ),
    "template",
)


class CodeGenerationHelper:
    def __init__(
        self,
        anthropic_client: AnthropicService = Depends(),
        error_repo: ErrorRepo = Depends(),
    ):
        """
        Initializes the CodeGenerationHelper.
        """
        self.anthropic_client = anthropic_client
        self.error_repo = error_repo

    @staticmethod
    def load_endpoints(filepath: str) -> List[Dict[str, Any]]:
        """
        Load endpoints from the JSON file.

        Args:
            filepath: Path to the JSON file containing endpoints

        Returns:
            List of endpoint dictionaries

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
            KeyError: If the expected structure is not found
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Endpoints file not found: {filepath}")

            with open(filepath, "r") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError(
                    f"Expected JSON object in file {filepath}, got {type(data)}"
                )

            endpoints = data.get("endpoints", [])
            if not isinstance(endpoints, list):
                raise ValueError(
                    f"Expected 'endpoints' to be a list in {filepath}, got {type(endpoints)}"
                )

            return endpoints
        except FileNotFoundError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise
        except json.JSONDecodeError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise ValueError(
                f"Invalid JSON format in file {filepath}: {str(e)}"
            )
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error loading endpoints from {filepath}: {str(e)}\n{stack_trace}"
            )

    @staticmethod
    def load_reference_template(filename: str) -> List[Dict[str, Any]]:
        """
        Load reference template from JSON file in the template directory.

        Args:
            filename: Name of the template file

        Returns:
            List of template dictionaries

        Raises:
            FileNotFoundError: If the template file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        path = os.path.join(TEMPLATE_DIR, filename)
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Template file not found: {path}")

            with open(path, "r") as f:
                template_data = json.load(f)

            if not isinstance(template_data, list):
                raise ValueError(
                    f"Expected JSON array in template file {path}, got {type(template_data)}"
                )

            return template_data
        except FileNotFoundError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise
        except json.JSONDecodeError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise ValueError(
                f"Invalid JSON format in template file {path}: {str(e)}"
            )
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error loading reference template {path}: {str(e)}\n{stack_trace}"
            )

    @staticmethod
    def extract_summary(
        endpoints: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract only the keys we care about from each endpoint.

        Args:
            endpoints: List of endpoint dictionaries

        Returns:
            List of endpoint summaries with selected fields

        Raises:
            ValueError: If the input is not a list
        """
        try:
            if not isinstance(endpoints, list):
                raise ValueError(
                    f"Expected list of endpoints, got {type(endpoints)}"
                )

            return [
                {
                    "endpointName": ep.get("endpointName"),
                    "method": ep.get("method"),
                    "path": ep.get(
                        "path", f"/{ep.get('endpointName', 'unknown')}"
                    ),
                    "description": ep.get("description"),
                    "authRequired": ep.get("authRequired"),
                    "requestBody": ep.get("requestBody"),
                    "responseBody": ep.get("responseBody"),
                    "database_schema": ep.get("database_schema"),
                }
                for ep in endpoints
            ]
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error extracting endpoint summaries: {str(e)}\n{stack_trace}"
            )

    @staticmethod
    def format_reference_code(template_files: List[Dict[str, Any]]) -> str:
        """
        Format reference code files for inclusion in the prompt.

        Args:
            template_files: List of template file dictionaries

        Returns:
            Formatted string with reference code

        Raises:
            ValueError: If the input is not a list
        """
        try:
            if not isinstance(template_files, list):
                raise ValueError(
                    f"Expected list of template files, got {type(template_files)}"
                )

            formatted_sections = []

            for file in template_files:
                if "file_path" in file and "code" in file:
                    formatted_sections.append(
                        f"### {file['file_path']}\n```javascript\n{file['code']}\n```"
                    )

            return "\n\n".join(formatted_sections)
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error formatting reference code: {str(e)}\n{stack_trace}"
            )

    @staticmethod
    def build_full_codebase_prompt(
        project_name: str,
        endpoints: List[Dict[str, Any]],
        auth_template: Optional[List[Dict[str, Any]]] = None,
        db_template: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build a comprehensive prompt for generating the entire codebase using the prompt template.

        Args:
            project_name: Name of the project
            endpoints: List of endpoint summaries
            auth_template: Authentication template files
            db_template: Database template files

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        try:
            if not project_name:
                raise ValueError("Project name cannot be empty")

            if not isinstance(endpoints, list):
                raise ValueError(
                    f"Expected list of endpoints, got {type(endpoints)}"
                )

            endpoints_json = json.dumps(endpoints, indent=2)

            auth_reference = ""
            if auth_template and len(auth_template) > 0:
                auth_reference = "\n## Authentication Reference Templates\nUse these templates as reference for authentication implementation:\n\n"
                auth_reference += CodeGenerationHelper.format_reference_code(
                    auth_template
                )

            db_reference = ""
            if db_template and len(db_template) > 0:
                db_reference = "\n## Database Reference Templates\nUse these templates as reference for database implementation:\n\n"
                db_reference += CodeGenerationHelper.format_reference_code(
                    db_template
                )

            prompt = CODE_GENERATION_PROMPT.format(
                project_name=project_name,
                endpoints_json=endpoints_json,
                auth_reference=auth_reference,
                db_reference=db_reference,
            )

            if not prompt:
                raise ValueError("Generated prompt is empty")

            return prompt

        except KeyError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise ValueError(f"Missing key in prompt template: {str(e)}")
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(f"Error building prompt: {str(e)}\n{stack_trace}")

    @staticmethod
    def parse_json_response(response: str) -> List[Dict[str, Any]]:
        """
        Parse the JSON array response from Claude.

        Args:
            response: String response from Claude

        Returns:
            List of generated file dictionaries

        Raises:
            ValueError: If the response cannot be parsed
        """
        try:
            if not response:
                raise ValueError("Empty response from Claude")

            result = parse_response(response)

            if not isinstance(result, list):
                raise ValueError(f"Expected list of files, got {type(result)}")

            # Validate the structure of the result
            for i, file in enumerate(result):
                if not isinstance(file, dict):
                    raise ValueError(
                        f"Expected file at index {i} to be a dictionary, got {type(file)}"
                    )

                if "file_path" not in file:
                    raise ValueError(
                        f"Missing 'file_path' in file at index {i}"
                    )

                if "code" not in file:
                    raise ValueError(f"Missing 'code' in file at index {i}")

            return result

        except json.JSONDecodeError as e:
            # Can't log to MongoDB in a static method - handled by caller
            raise ValueError(f"Invalid JSON in Claude response: {str(e)}")
        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error parsing Claude response: {str(e)}\n{stack_trace}"
            )

    @staticmethod
    async def save_json_output(
        files: List[Dict[str, Any]], output_path: str
    ) -> None:
        """
        Save the generated files as JSON asynchronously.

        Args:
            files: List of generated file dictionaries
            output_path: Path to save the JSON output

        Raises:
            ValueError: If the files or output_path are invalid
            IOError: If there's an error writing to the file
        """
        try:
            if not files:
                raise ValueError("No files to save")

            if not output_path:
                raise ValueError("Output path cannot be empty")

            if not isinstance(files, list):
                raise ValueError(f"Expected list of files, got {type(files)}")

            # Ensure the directory exists
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                raise ValueError(
                    f"Output directory does not exist: {output_dir}"
                )

            # Prepare parameters for store_json_response
            params = {
                "response": files,
                "file_path": output_path,
            }

            # Store the response
            await store_json_response(params)

            # Verify the file was created
            if not os.path.exists(output_path):
                raise IOError(f"Failed to save output to {output_path}")

        except Exception as e:
            # Can't log to MongoDB in a static method - handled by caller
            stack_trace = traceback.format_exc()
            raise ValueError(
                f"Error saving JSON output to {output_path}: {str(e)}\n{stack_trace}"
            )

    async def _log_error(self, error_message: str) -> None:
        """Log error to MongoDB using ErrorRepo"""
        try:
            error = Error(error_message=error_message)
            await self.error_repo.insert_error(error)
        except Exception as e:
            # If logging to MongoDB fails, we don't want to throw another exception
            # This would be handled by the monitoring system in production
            pass
