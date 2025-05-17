import os
from fastapi import Depends
from src.app.usecases.clone_usecase.helper import CloneHelper

class CloneUseCase:
    def __init__(self, clone_helper: CloneHelper = Depends(CloneHelper)) -> None:
        self.clone_helper = clone_helper
    
    async def execute(self, github_url: str) -> dict:
        """
        Clone a GitHub repository to a unique directory.
        
        Args:
            github_url (str): The GitHub repository URL to clone
            
        Returns:
            dict: Information about the cloned repository including its path
        """
        # Validate GitHub URL
        self.clone_helper.validate_github_url(github_url)
        
        # Generate a UUID for the project directory
        project_uuid = self.clone_helper.generate_project_uuid()
        
        # Create project directory
        project_path = self.clone_helper.create_project_directory(project_uuid)
        
        # Clone the repository
        clone_result = self.clone_helper.clone_repository(github_url, project_path)
        
        # Add the UUID to the result
        clone_result["project_uuid"] = project_uuid
        
        return clone_result