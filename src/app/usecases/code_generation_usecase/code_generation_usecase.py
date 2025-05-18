from fastapi import Depends
import os
from src.app.services.anthropic_service import AnthropicService
from src.app.usecases.code_generation_usecase.helper import CodeGenerationHelper

class CodeGenerationUseCase:
    def __init__(self, anthropic_service: AnthropicService = Depends(AnthropicService)):
        self.anthropic_service = anthropic_service

    async def execute(
        self,
        input_path: str,
        project_name: str,
        auth_filename: str = "auth.json",
        db_filename: str = "database.json",
    ):
        # Load endpoints
        print(f"Loading endpoints from {input_path}...")
        endpoints = CodeGenerationHelper.load_endpoints(input_path)
        endpoints_summary = CodeGenerationHelper.extract_summary(endpoints)
        print(f"Loaded {len(endpoints)} endpoints")

        # Load reference templates
        print("Loading reference templates...")
        auth_template = CodeGenerationHelper.load_reference_template(auth_filename)
        db_template = CodeGenerationHelper.load_reference_template(db_filename)
        print(f"Loaded {len(auth_template)} auth reference files and {len(db_template)} database reference files")

        # Build prompt
        print("Building prompt...")
        prompt = CodeGenerationHelper.build_full_codebase_prompt(
            project_name, endpoints_summary, auth_template, db_template
        )
        print("Prompt built successfully")

        # Call AnthropicService to stream completions
        print("\nCalling Claude API to generate codebase...")
        print("This may take a few minutes...\n")
        print("----- Claude API Response -----")
        response_text = ""
        async for chunk_type, chunk_content in self.anthropic_service.stream_completions(
            user_prompt=prompt,
            system_prompt="You are a senior backend architect specializing in Node.js API development. Always use ES Module syntax (import/export) instead of CommonJS (require/module.exports). Include .js file extensions in all import paths. Create a consistent, modern architecture.",
            thinking_budget=0,
        ):
            if chunk_type == "text_delta":
                print(chunk_content, end="", flush=True)
                response_text += chunk_content
        print("\n------------------------------\n")

        # Parse the response
        print("Parsing response...")
        files = CodeGenerationHelper.parse_json_response(response_text)
        print(f"Successfully parsed {len(files)} files")

        # Save the files as final_code.json in the same directory as input_path
        input_dir = os.path.dirname(input_path)
        output_path = os.path.join(input_dir, "final_code.json")
        await CodeGenerationHelper.save_json_output(files, output_path)
        return output_path
