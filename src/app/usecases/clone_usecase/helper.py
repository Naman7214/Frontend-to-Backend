import asyncio
import os
import re
import uuid

from fastapi import HTTPException


class CloneHelper:
    def __init__(self) -> None:
        # Base directory for all cloned projects
        self.projects_dir = "Projects"

    async def validate_github_url(self, github_url: str) -> bool:
        """
        Validate if the provided URL is a valid GitHub repository URL.

        Args:
            github_url (str): The GitHub URL to validate

        Returns:
            bool: True if valid, raises an exception otherwise
        """
        # Pattern for GitHub URLs (both HTTPS and SSH formats)
        https_pattern = r"^https:\/\/github\.com\/[^\/]+\/[^\/]+(?:\.git)?$"
        ssh_pattern = r"^git@github\.com:[^\/]+\/[^\/]+(?:\.git)?$"

        if re.match(https_pattern, github_url) or re.match(
            ssh_pattern, github_url
        ):
            return True

        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL format. URL should be in the format: 'https://github.com/username/repo' or 'git@github.com:username/repo'",
        )

    async def generate_project_uuid(self) -> str:
        """
        Generate a unique UUID for the project directory.

        Returns:
            str: A UUID string
        """
        return str(uuid.uuid4())

    async def get_repo_name_from_url(self, github_url: str) -> str:
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

    async def create_project_directory(self, project_uuid: str) -> str:
        """
        Create a project directory with the given UUID.

        Args:
            project_uuid (str): UUID for the project directory

        Returns:
            str: Path to the created directory
        """
        # Ensure the base projects directory exists
        os.makedirs(self.projects_dir, exist_ok=True)
        print(f"Projects directory: {self.projects_dir}")

        # Create the specific project directory
        project_path = os.path.join(self.projects_dir, project_uuid)
        os.makedirs(project_path, exist_ok=True)
        print(f"Project path: {project_path}")
        return project_path

    async def clone_repository(self, github_url: str, project_dir: str) -> dict:
        """
        Clone a GitHub repository to the project directory path asynchronously.
        Creates a subdirectory with the repository name.

        Args:
            github_url (str): The GitHub URL to clone
            project_dir (str): Base project directory (Projects/uuid/)

        Returns:
            dict: Information about the cloned repository
        """
        try:
            # Get repo name from URL to create the subdirectory
            repo_name = await self.get_repo_name_from_url(github_url)

            # Create the full destination path: Projects/uuid/repo_name
            destination_path = os.path.join(project_dir, repo_name)

            # Make destination_path absolute to avoid path issues
            abs_destination_path = os.path.abspath(destination_path)
            abs_project_dir = os.path.abspath(project_dir)

            # Run git clone command asynchronously
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                github_url,
                abs_destination_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                stderr_text = stderr.decode()
                # Check if the error is because the repository is private or doesn't exist
                if (
                    "Authentication failed" in stderr_text
                    or "could not read Username" in stderr_text
                ):
                    error_message = "Private repository or authentication required. Please provide credentials."
                elif "repository not found" in stderr_text:
                    error_message = (
                        "Repository not found. Please check the URL."
                    )
                else:
                    error_message = f"Git clone failed: {stderr_text}"

                raise HTTPException(status_code=400, detail=error_message)

            # Verify the directory exists after cloning
            if not os.path.exists(abs_destination_path):
                raise HTTPException(
                    status_code=500,
                    detail=f"Repository directory was not created at {abs_destination_path}",
                )

            # Get commit count to verify successful clone asynchronously
            commit_count_process = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                abs_destination_path,
                "rev-list",
                "--count",
                "HEAD",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await commit_count_process.communicate()
            commit_count = (
                int(stdout.decode().strip())
                if commit_count_process.returncode == 0
                else 0
            )

            return {
                "success": True,
                "repo_name": repo_name,
                "repo_path": abs_destination_path,  # Path to cloned repo (Projects/uuid/repo_name)
                "project_dir": abs_project_dir,  # Path to project dir (Projects/uuid/)
                "commit_count": commit_count,
                "message": "Repository cloned successfully.",
            }

        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to clone repository in clone_usecase.helper: {str(e)}"
            )