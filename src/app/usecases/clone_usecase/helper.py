import os
import re
import uuid
import subprocess
from pathlib import Path
from fastapi import HTTPException

class CloneHelper:
    def __init__(self) -> None:
        # Base directory for all cloned projects
        self.projects_dir = "Projects"
        
    def validate_github_url(self, github_url: str) -> bool:
        """
        Validate if the provided URL is a valid GitHub repository URL.
        
        Args:
            github_url (str): The GitHub URL to validate
            
        Returns:
            bool: True if valid, raises an exception otherwise
        """
        # Pattern for GitHub URLs (both HTTPS and SSH formats)
        https_pattern = r'^https:\/\/github\.com\/[^\/]+\/[^\/]+(?:\.git)?$'
        ssh_pattern = r'^git@github\.com:[^\/]+\/[^\/]+(?:\.git)?$'
        
        if re.match(https_pattern, github_url) or re.match(ssh_pattern, github_url):
            return True
        
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL format. URL should be in the format: 'https://github.com/username/repo' or 'git@github.com:username/repo'"
        )
    
    def generate_project_uuid(self) -> str:
        """
        Generate a unique UUID for the project directory.
        
        Returns:
            str: A UUID string
        """
        return str(uuid.uuid4())
    
    def get_repo_name_from_url(self, github_url: str) -> str:
        """
        Extract repository name from GitHub URL.
        
        Args:
            github_url (str): The GitHub URL
            
        Returns:
            str: Repository name
        """
        # For HTTPS URLs
        if github_url.startswith("https://"):
            parts = github_url.rstrip("/").split("/")
            repo_name = parts[-1]
        # For SSH URLs
        else:
            parts = github_url.split(":")
            repo_name = parts[-1].split("/")[-1]
        
        # Remove .git extension if present
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
            
        return repo_name
    
    def create_project_directory(self, project_uuid: str) -> str:
        """
        Create a project directory with the given UUID.
        
        Args:
            project_uuid (str): UUID for the project directory
            
        Returns:
            str: Path to the created directory
        """
        # Ensure the base projects directory exists
        os.makedirs(self.projects_dir, exist_ok=True)
        
        # Create the specific project directory
        project_path = os.path.join(self.projects_dir, project_uuid)
        os.makedirs(project_path, exist_ok=True)
        
        return project_path
    
    def clone_repository(self, github_url: str, destination_path: str) -> dict:
        """
        Clone a GitHub repository to the specified path.
        
        Args:
            github_url (str): The GitHub URL to clone
            destination_path (str): Path where to clone the repository
            
        Returns:
            dict: Information about the cloned repository
        """
        try:
            # Run git clone command
            process = subprocess.run(
                ["git", "clone", github_url, destination_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get repo name
            repo_name = self.get_repo_name_from_url(github_url)
            
            # Get commit count to verify successful clone
            os.chdir(destination_path)
            commit_count_process = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True
            )
            commit_count = int(commit_count_process.stdout.strip()) if commit_count_process.returncode == 0 else 0
            
            return {
                "success": True,
                "repo_name": repo_name,
                "repo_path": destination_path,
                "commit_count": commit_count,
                "message": "Repository cloned successfully."
            }
            
        except subprocess.CalledProcessError as e:
            # Check if the error is because the repository is private or doesn't exist
            if "Authentication failed" in e.stderr or "could not read Username" in e.stderr:
                error_message = "Private repository or authentication required. Please provide credentials."
            elif "repository not found" in e.stderr:
                error_message = "Repository not found. Please check the URL."
            else:
                error_message = f"Git clone failed: {e.stderr}"
                
            raise HTTPException(
                status_code=400,
                detail=error_message
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clone repository: {str(e)}"
            )