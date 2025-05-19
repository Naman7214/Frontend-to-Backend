import os
import traceback
from typing import Any, Dict

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.usecases.clone_usecase.helper import CloneHelper


class CloneUseCase:
    def __init__(
        self,
        clone_helper: CloneHelper = Depends(CloneHelper),
        error_repo: ErrorRepo = Depends(ErrorRepo),
    ) -> None:
        self.clone_helper = clone_helper
        self.error_repo = error_repo

    async def execute(self, github_url: str) -> Dict[str, Any]:
        """
        Clone a GitHub repository to a unique directory asynchronously.

        Args:
            github_url (str): The GitHub repository URL to clone

        Returns:
            Dict[str, Any]: Information about the cloned repository
        """
        try:
            # Validate GitHub URL
            await self.clone_helper.validate_github_url(github_url)

            # Generate a UUID for the project directory
            project_uuid = await self.clone_helper.generate_project_uuid()

            # Create project directory
            project_dir = await self.clone_helper.create_project_directory(
                project_uuid
            )

            # Clone the repository asynchronously
            # Now the repository will be cloned to Projects/uuid/repo_name
            clone_result = await self.clone_helper.clone_repository(
                github_url, project_dir
            )

            # Add the UUID to the result
            clone_result["project_uuid"] = project_uuid

            # Define the endpoints.json path in the project directory (not in the repo directory)
            endpoints_path = os.path.join(project_dir, "endpoints.json")
            clone_result["endpoints_path"] = endpoints_path

            return clone_result

        except HTTPException as http_ex:
            # Log the error to MongoDB
            error_message = f"HTTP Exception in CloneUseCase.execute: {http_ex.detail} - Status code: {http_ex.status_code}"
            error = Error(error_message)
            await self.error_repo.insert_error(error)

            # Re-raise the exception to be handled by the API layer
            raise

        except ValueError as val_ex:
            # Handle validation errors
            error_message = (
                f"Validation error in CloneUseCase.execute: {str(val_ex)}"
            )
            error = Error(error_message)
            await self.error_repo.insert_error(error)

            # Convert to HTTP exception with appropriate status code
            raise HTTPException(status_code=400, detail=str(val_ex))

        except OSError as os_ex:
            # Handle file system errors
            error_message = (
                f"File system error in CloneUseCase.execute: {str(os_ex)}"
            )
            error = Error(error_message)
            await self.error_repo.insert_error(error)

            raise HTTPException(
                status_code=500,
                detail=f"File system operation failed: {str(os_ex)}",
            )

        except Exception as ex:
            # Get stack trace for detailed error logging
            stack_trace = traceback.format_exc()

            # Create a detailed error message
            error_message = (
                f"Unexpected error in CloneUseCase.execute while processing URL {github_url}: "
                f"{str(ex)}\nStack trace: {stack_trace}"
            )

            # Log the error to MongoDB
            error = Error(error_message)
            await self.error_repo.insert_error(error)

            # Raise a generic HTTP exception with a user-friendly message
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while cloning the repository.",
            )
