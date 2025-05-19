import os
import traceback

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.anthropic_service import AnthropicService
from src.app.usecases.code_generation_usecase.helper import CodeGenerationHelper


class CodeGenerationUseCase:
    def __init__(
        self,
        anthropic_service: AnthropicService = Depends(AnthropicService),
        error_repo: ErrorRepo = Depends(),
    ):
        self.anthropic_service = anthropic_service
        self.error_repo = error_repo

    async def execute(
        self,
        input_path: str,
        project_name: str,
        auth_filename: str = "auth.json",
        db_filename: str = "database.json",
    ) -> str:
        """
        Execute code generation process using Anthropic API.

        Args:
            input_path: Path to the input endpoints file
            project_name: Name of the project to generate
            auth_filename: Name of the auth template file
            db_filename: Name of the database template file

        Returns:
            Path to the generated output file

        Raises:
            HTTPException: If any step in the process fails
        """
        try:
            # Validate input path
            if not input_path or not os.path.exists(input_path):
                error_msg = f"Error in CodeGenerationUseCase.execute: Input file not found: {input_path}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=404,
                    detail=f"Input file not found: {input_path}",
                )

            # Validate project name
            if not project_name:
                error_msg = "Error in CodeGenerationUseCase.execute: Project name cannot be empty"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=400, detail="Project name cannot be empty"
                )

            # Load endpoints
            try:
                endpoints = CodeGenerationHelper.load_endpoints(input_path)
                if not endpoints:
                    error_msg = f"Error in CodeGenerationUseCase.execute: No endpoints found in file: {input_path}"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=400,
                        detail=f"No endpoints found in file: {input_path}",
                    )

                endpoints_summary = CodeGenerationHelper.extract_summary(
                    endpoints
                )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to load endpoints from {input_path}. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load endpoints: {str(e)}",
                )

            # Load reference templates
            try:
                auth_template = CodeGenerationHelper.load_reference_template(
                    auth_filename
                )
                db_template = CodeGenerationHelper.load_reference_template(
                    db_filename
                )

                if not auth_template:
                    error_msg = f"Error in CodeGenerationUseCase.execute: Failed to load auth template: {auth_filename}"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to load auth template: {auth_filename}",
                    )

                if not db_template:
                    error_msg = f"Error in CodeGenerationUseCase.execute: Failed to load database template: {db_filename}"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to load database template: {db_filename}",
                    )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to load reference templates. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load reference templates: {str(e)}",
                )

            # Build prompt
            try:
                prompt = CodeGenerationHelper.build_full_codebase_prompt(
                    project_name, endpoints_summary, auth_template, db_template
                )
                if not prompt:
                    error_msg = "Error in CodeGenerationUseCase.execute: Failed to build prompt - empty result"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500, detail="Failed to build prompt"
                    )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to build prompt. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500, detail=f"Failed to build prompt: {str(e)}"
                )

            # Call AnthropicService to stream completions
            response_text = ""
            try:
                async for (
                    chunk_type,
                    chunk_content,
                ) in self.anthropic_service.stream_completions(
                    user_prompt=prompt,
                    system_prompt="You are a senior backend architect specializing in Node.js API development. Always use ES Module syntax (import/export) instead of CommonJS (require/module.exports). Include .js file extensions in all import paths. Create a consistent, modern architecture.",
                    thinking_budget=0,
                ):
                    if chunk_type == "text_delta":
                        response_text += chunk_content
                        print(chunk_content, end="", flush=True)


                if not response_text:
                    error_msg = "Error in CodeGenerationUseCase.execute: Empty response from Anthropic API"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500, detail="Empty response from AI service"
                    )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to get response from Anthropic API. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500, detail=f"Failed to generate code: {str(e)}"
                )

            # Parse the response
            try:
                files = CodeGenerationHelper.parse_json_response(response_text)
                if not files:
                    error_msg = "Error in CodeGenerationUseCase.execute: Failed to parse response - no files generated"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to parse response - no files generated",
                    )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to parse response. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse response: {str(e)}",
                )

            # Save the files as final_code.json in the same directory as input_path
            try:
                input_dir = os.path.dirname(input_path)
                output_path = os.path.join(input_dir, "final_code.json")
                await CodeGenerationHelper.save_json_output(files, output_path)

                if not os.path.exists(output_path):
                    error_msg = f"Error in CodeGenerationUseCase.execute: Failed to save output to {output_path}"
                    await self._log_error(error_msg)
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to save output to {output_path}",
                    )
            except Exception as e:
                error_msg = f"Error in CodeGenerationUseCase.execute: Failed to save output. Error: {str(e)}"
                await self._log_error(error_msg)
                raise HTTPException(
                    status_code=500, detail=f"Failed to save output: {str(e)}"
                )

            return output_path

        except HTTPException:
            # Re-raise HTTPExceptions as they're already formatted properly
            raise
        except Exception as e:
            # Handle any unexpected exceptions
            stack_trace = traceback.format_exc()
            error_msg = f"Unexpected error in CodeGenerationUseCase.execute: {str(e)}. Trace: {stack_trace}"
            await self._log_error(error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}",
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
