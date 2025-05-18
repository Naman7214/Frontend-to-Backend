import json
import os
import shutil
import zipfile

class CodeConstructorUseCase:
    def __init__(self, ):
        pass
    def execute(self, code_json_path):
        """
        Reads JSON file containing code structure and creates the directory structure with files,
        then zips the entire directory.
        
        Args:
            code_json_path (str): Path to the JSON file containing code structure
            
        Returns:
            str: Path to the created ZIP file containing the api directory
        """
        # Get directory where the JSON file is located
        json_dir = os.path.dirname(code_json_path)
        
        # Create api directory in the same folder as the JSON
        api_dir = os.path.join(json_dir, "api")
        
        # If the api directory already exists, remove it to start fresh
        if os.path.exists(api_dir):
            shutil.rmtree(api_dir)
            
        # Create the api directory
        os.makedirs(api_dir)
        
        # Read the JSON file
        with open(code_json_path, 'r') as file:
            files_data = json.load(file)
            
        # Create each file and its parent directories
        for file_info in files_data:
            file_path = file_info.get("file_path")
            code = file_info.get("code")
            
            # Skip if either is missing
            if not file_path or code is None:
                continue
                
            # Create the full path for the file
            full_path = os.path.join(api_dir, file_path)
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write the file content
            with open(full_path, 'w') as f:
                f.write(code)
        
        # Create ZIP file of the api directory
        zip_path = os.path.join(json_dir, "api.zip")
        
        # Remove existing zip file if it exists
        if os.path.exists(zip_path):
            os.remove(zip_path)
            
        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all files and directories in the api directory
            for root, dirs, files in os.walk(api_dir):
                for file in files:
                    # Get the full path of the file
                    file_path = os.path.join(root, file)
                    # Get the relative path to include in the zip
                    rel_path = os.path.relpath(file_path, os.path.dirname(api_dir))
                    # Add the file to the zip
                    zipf.write(file_path, rel_path)
        
        return zip_path
