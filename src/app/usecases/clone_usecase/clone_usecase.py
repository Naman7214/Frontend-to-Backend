import os
from fastapi import Depends
from src.app.usecases.clone_usecase.helper import CloneHelper
from typing import Tuple

class CloneUseCase:
    def __init__(self, clone_helper: CloneHelper = Depends(CloneHelper)) -> None:
        self.clone_helper = clone_helper
    
    async def execute(self, github_url: str) -> Tuple[str, str]:
        """
        Clone a GitHub repository to a unique directory asynchronously.
        
        Args:
            github_url (str): The GitHub repository URL to clone
            
        Returns:
            Tuple[str, str]: A tuple containing (repo_path, project_uuid)
        """
        # Validate GitHub URL
        self.clone_helper.validate_github_url(github_url)
        
        # Generate a UUID for the project directory
        project_uuid = self.clone_helper.generate_project_uuid()
        
        # Create project directory
        project_path = self.clone_helper.create_project_directory(project_uuid)
        
        # Clone the repository asynchronously
        clone_result = await self.clone_helper.clone_repository(github_url, project_path)
        
        repo_path = clone_result["repo_path"]
        
        return repo_path, project_uuid