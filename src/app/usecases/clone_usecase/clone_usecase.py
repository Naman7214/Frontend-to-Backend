import os
from fastapi import Depends
from src.app.usecases.clone_usecase.helper import CloneHelper
from typing import Dict, Any

class CloneUseCase:
    def __init__(self, clone_helper: CloneHelper = Depends(CloneHelper)) -> None:
        self.clone_helper = clone_helper
    
    async def execute(self, github_url: str) -> Dict[str, Any]:
        """
        Clone a GitHub repository to a unique directory asynchronously.
        
        Args:
            github_url (str): The GitHub repository URL to clone
            
        Returns:
            Dict[str, Any]: Information about the cloned repository
        """
        # Validate GitHub URL
        self.clone_helper.validate_github_url(github_url)
        
        # Generate a UUID for the project directory
        project_uuid = self.clone_helper.generate_project_uuid()
        
        # Create project directory
        project_dir = self.clone_helper.create_project_directory(project_uuid)
        
        # Clone the repository asynchronously
        # Now the repository will be cloned to Projects/uuid/repo_name
        clone_result = await self.clone_helper.clone_repository(github_url, project_dir)
        
        # Add the UUID to the result
        clone_result["project_uuid"] = project_uuid
        
        # Define the endpoints.json path in the project directory (not in the repo directory)
        endpoints_path = os.path.join(project_dir, "endpoints.json")
        clone_result["endpoints_path"] = endpoints_path
        
        return clone_result