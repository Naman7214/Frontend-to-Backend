import os
import json
from fastapi import Depends
from src.app.services.anthropic_service import AnthropicService
from src.app.utils.response_parser import parse_response
from src.app.utils.store_response import store_json_response
from src.app.prompts.code_generation_prompt import CODE_GENERATION_PROMPT

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'template')

class CodeGenerationHelper:
    def __init__(self, anthropic_client: AnthropicService = Depends()):
        """
        Initializes the CodeGenerationHelper.
        """
        self.anthropic_client = anthropic_client
        pass
    """
    Helper class for code generation.
    """

    @staticmethod
    def load_endpoints(filepath):
        """Load endpoints from the JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data.get('endpoints', [])

    @staticmethod
    def load_reference_template(filename):
        """Load reference template from JSON file in the template directory."""
        path = os.path.join(TEMPLATE_DIR, filename)
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load reference template {path}: {e}")
            return []
    
    @staticmethod
    def extract_summary(endpoints):
        """Extract only the keys we care about from each endpoint."""
        return [
            {
                "endpointName": ep.get("endpointName"),
                "method": ep.get("method"),
                "path": ep.get("path", f"/{ep.get('endpointName', 'unknown')}"),
                "description": ep.get("description"),
                "authRequired": ep.get("authRequired"),
                "requestBody": ep.get("requestBody"),
                "responseBody": ep.get("responseBody"),
                "database_schema": ep.get("database_schema"),
            }
            for ep in endpoints
        ]

    @staticmethod
    def format_reference_code(template_files):
        """Format reference code files for inclusion in the prompt."""
        formatted_sections = []
        
        for file in template_files:
            if 'file_path' in file and 'code' in file:
                formatted_sections.append(f"### {file['file_path']}\n```javascript\n{file['code']}\n```")
        
        return "\n\n".join(formatted_sections)
    
    @staticmethod
    def build_full_codebase_prompt(project_name, endpoints, auth_template=None, db_template=None):
        """Build a comprehensive prompt for generating the entire codebase using the prompt template."""
        endpoints_json = json.dumps(endpoints, indent=2)
        auth_reference = ""
        if auth_template and len(auth_template) > 0:
            auth_reference = "\n## Authentication Reference Templates\nUse these templates as reference for authentication implementation:\n\n"
            auth_reference += CodeGenerationHelper.format_reference_code(auth_template)
        db_reference = ""
        if db_template and len(db_template) > 0:
            db_reference = "\n## Database Reference Templates\nUse these templates as reference for database implementation:\n\n"
            db_reference += CodeGenerationHelper.format_reference_code(db_template)
        print("ABOUT TO BUILD PROMPT")
        try:
            prompt = CODE_GENERATION_PROMPT.format(
            project_name=project_name,
            endpoints_json=endpoints_json,
            auth_reference=auth_reference,
            db_reference=db_reference
            )
        except Exception as e:
            print(f"Error building prompt: {e}")
            prompt = ""
        print("PROMPT BUILT")
        return prompt

    @staticmethod
    def parse_json_response(response):
        """Parse the JSON array response from Claude."""
        return parse_response(response)

    @staticmethod
    async def save_json_output(files, output_path):
        """Save the generated files as JSON asynchronously."""
        await store_json_response({"response": files, "file_path": output_path})
    
    