from fastapi import Depends
from src.app.usecases.endpoint_usecase.helper import EndpointHelper
import os
import json
from typing import Dict, Any

class EndpointUseCase:
    def __init__(self, endpoint_helper: EndpointHelper = Depends(EndpointHelper)) -> None:
        self.endpoint_helper = endpoint_helper
    
    async def execute(self, repo_path: str, output_path: str = None, verbose: bool = False, max_files: int = None, 
                     all_files: bool = False, api_files: bool = False, react_hooks: bool = False, 
                     auth_files: bool = False) -> Dict[str, Any]:
        """
        Extract API endpoint specifications from a React codebase.
        
        Args:
            repo_path (str): Path to the React repository to analyze
            output_path (str, optional): Path to save JSON output. Defaults to None.
            verbose (bool, optional): Print verbose output during processing. Defaults to False.
            max_files (int, optional): Maximum number of files to analyze. Defaults to None (no limit).
            all_files (bool, optional): Analyze all JS/TS files. Defaults to False.
            api_files (bool, optional): Target API-related files. Defaults to False.
            react_hooks (bool, optional): Find files using React hooks. Defaults to False.
            auth_files (bool, optional): Find auth-related files. Defaults to False.
            
        Returns:
            Dict[str, Any]: Dictionary with "endpoints" key containing a list of endpoint specifications
        """
        # Validate repo_path exists
        if not os.path.isdir(repo_path):
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        # Extract endpoints
        result = await self.endpoint_helper.extract_endpoints(
            root_dir=repo_path,
            verbose=verbose,
            max_files=max_files,
            all_files=all_files,
            api_files=api_files,
            react_hooks=react_hooks,
            auth_files=auth_files
        )
        
        # Save to output file if specified
        if output_path:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Write the JSON output
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
                
            if verbose:
                print(f"Saved endpoints to {output_path}")
            
            # Add the output path to the result
            result["output_path"] = output_path
                
        return output_path
