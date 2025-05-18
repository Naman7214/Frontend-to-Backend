import asyncio
import glob
import json
import os
import re

import aiofiles
from fastapi import Depends

from src.app.prompts.endpoint_prompt import ENDPOINT_PROMPT_SYSTEM_PROMPT
from src.app.services.openai_service import OpenAIService


class EndpointHelper:
    def __init__(
        self, openai_service: OpenAIService = Depends(OpenAIService)
    ) -> None:
        self.openai_service = openai_service
        self.system_prompt = ENDPOINT_PROMPT_SYSTEM_PROMPT

    async def find_files_with_grep(
        self, root_dir, patterns, file_extensions=None
    ):
        """
        Find files containing specific patterns using grep-like search (async version).
        Returns list of matching file paths.
        """
        matching_files = set()
        extensions = file_extensions or [".js", ".jsx", ".ts", ".tsx"]

        for pattern in patterns:
            try:
                try:
                    # Use async subprocess for grep operation
                    ext_pattern = " -o ".join(
                        [f"-name '*{ext}'" for ext in extensions]
                    )
                    cmd = f"find {root_dir} -type f \\( {ext_pattern} \\) -exec grep -l '{pattern}' {{}} \\;"
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    if stdout:
                        files = stdout.decode().strip().split("\n")
                        matching_files.update([f for f in files if f])
                except Exception as e:
                    # Fallback to Python-based search (async version)
                    for ext in extensions:
                        for file_path in glob.glob(
                            os.path.join(root_dir, "**", f"*{ext}"),
                            recursive=True,
                        ):
                            try:
                                async with aiofiles.open(
                                    file_path, "r", encoding="utf-8"
                                ) as f:
                                    content = await f.read()
                                    if re.search(pattern, content):
                                        matching_files.add(file_path)
                            except:
                                # Skip files with encoding issues
                                pass
            except Exception as e:
                print(f"Error searching for pattern '{pattern}': {e}")

        return list(matching_files)

    async def find_react_files(
        self,
        root_dir,
        all_files=False,
        api_files=False,
        react_hooks=False,
        auth_files=False,
    ):
        """Find React files in the codebase based on specified criteria (async version)."""
        result_files = []

        # Define patterns for file discovery
        patterns = []

        if all_files:
            # Find all JS/TS React files
            patterns.extend(
                [
                    os.path.join(root_dir, "**", "*.jsx"),
                    os.path.join(root_dir, "**", "*.tsx"),
                    os.path.join(
                        root_dir, "**", "*.js"
                    ),  # Include regular JS files too
                    os.path.join(
                        root_dir, "**", "*.ts"
                    ),  # Include TypeScript files
                ]
            )
        elif api_files:
            # Find files likely to contain API definitions
            patterns.extend(
                [
                    os.path.join(root_dir, "**", "*api*.js"),
                    os.path.join(root_dir, "**", "*api*.ts"),
                    os.path.join(root_dir, "**", "*api*.jsx"),
                    os.path.join(root_dir, "**", "*api*.tsx"),
                    os.path.join(root_dir, "**", "*service*.js"),
                    os.path.join(root_dir, "**", "*service*.ts"),
                    os.path.join(root_dir, "**", "*client*.js"),
                    os.path.join(root_dir, "**", "*client*.ts"),
                    os.path.join(root_dir, "**", "*http*.js"),
                    os.path.join(root_dir, "**", "*http*.ts"),
                    os.path.join(root_dir, "src", "api", "**", "*.js"),
                    os.path.join(root_dir, "src", "api", "**", "*.ts"),
                    os.path.join(root_dir, "src", "services", "**", "*.js"),
                    os.path.join(root_dir, "src", "services", "**", "*.ts"),
                ]
            )
        else:
            # Default: find only index files
            patterns.extend(
                [
                    os.path.join(root_dir, "**", "index.jsx"),
                    os.path.join(root_dir, "**", "index.tsx"),
                    os.path.join(
                        root_dir, "**", "index.js"
                    ),  # Include JS index files
                    os.path.join(
                        root_dir, "**", "index.ts"
                    ),  # Include TS index files
                ]
            )

        # Collect files from all patterns (this is synchronous but fast)
        for pattern in patterns:
            result_files.extend(glob.glob(pattern, recursive=True))

        # Always perform basic API-related searches even in normal execution
        # These patterns cover the most common API usage in React code
        api_fetch_patterns = [
            "useEffect",
            "useQuery",
            "useMutation",
            "useState",
        ]
        # Call the async method with await
        api_files = await self.find_files_with_grep(
            root_dir, api_fetch_patterns
        )
        result_files.extend(api_files)

        # Add files containing React hooks for data fetching if explicitly requested
        if react_hooks:
            hook_patterns = [
                "useEffect",
                "useQuery",
                "useMutation",
                "useApi",
                "useFetch",
                "useHttp",
                "useRequest",
            ]
            # Call the async method with await
            hook_files = await self.find_files_with_grep(
                root_dir, hook_patterns
            )
            result_files.extend(hook_files)

        # Add files with auth-related keywords if explicitly requested
        if auth_files:
            auth_patterns = [
                "auth",
                "login",
                "logout",
                "signin",
                "signup",
                "token",
                "jwt",
                "password",
            ]
            # Call the async method with await
            auth_files = await self.find_files_with_grep(
                root_dir, auth_patterns
            )
            result_files.extend(auth_files)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file in result_files:
            if file not in seen:
                seen.add(file)
                unique_files.append(file)

        return unique_files

    async def read_file(self, file_path):
        """Read a file's contents as text (async version)."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return f"[ERROR: Could not read file: {str(e)}]"

    def get_relative_path(self, file_path, root_dir):
        """Convert absolute path to relative path from root_dir."""
        abs_root = os.path.abspath(root_dir)
        abs_file = os.path.abspath(file_path)
        return os.path.relpath(abs_file, abs_root)

    def update_endpoints_list(self, existing_endpoints, new_endpoints):
        """
        Update the existing endpoints list with new endpoints, merging where appropriate.
        Handles both modified endpoints and entirely new endpoints.
        """
        # Create a lookup map for existing endpoints by name and method
        endpoint_map = {}
        for endpoint in existing_endpoints:
            key = f"{endpoint['endpointName']}:{endpoint.get('method', 'UNKNOWN')}"
            endpoint_map[key] = endpoint

        # Process each new endpoint
        for new_endpoint in new_endpoints:
            key = f"{new_endpoint['endpointName']}:{new_endpoint.get('method', 'UNKNOWN')}"

            # If this is flagged as a modification of an existing endpoint
            if (
                new_endpoint.get("isModifiedEndpoint", False)
                and key in endpoint_map
            ):
                existing = endpoint_map[key]

                # Add this file to the used files list
                if "usedInFiles" not in existing:
                    existing["usedInFiles"] = []
                existing_files = set(existing["usedInFiles"])
                new_files = set(new_endpoint.get("usedInFiles", []))
                existing["usedInFiles"] = sorted(
                    list(existing_files.union(new_files))
                )

                # Take the most detailed description
                if len(new_endpoint.get("description", "")) > len(
                    existing.get("description", "")
                ):
                    existing["description"] = new_endpoint["description"]

                # Merge or update payload fields
                for field, details in new_endpoint.get("payload", {}).items():
                    if "payload" not in existing:
                        existing["payload"] = {}
                    existing["payload"][field] = details

                # Merge or update query parameters
                for param, details in new_endpoint.get(
                    "queryParams", {}
                ).items():
                    if "queryParams" not in existing:
                        existing["queryParams"] = {}
                    existing["queryParams"][param] = details

                # Merge or update response fields
                for field, details in new_endpoint.get("response", {}).items():
                    if "response" not in existing:
                        existing["response"] = {}
                    existing["response"][field] = details

                # Update other properties
                if new_endpoint.get("authRequired", False):
                    existing["authRequired"] = True
                if new_endpoint.get("databaseRequired", False):
                    existing["databaseRequired"] = True
                if new_endpoint.get("fileUpload", False):
                    existing["fileUpload"] = True

            # For entirely new endpoints
            elif key not in endpoint_map:
                # Remove the isModifiedEndpoint flag if present
                if "isModifiedEndpoint" in new_endpoint:
                    del new_endpoint["isModifiedEndpoint"]

                existing_endpoints.append(new_endpoint)
                endpoint_map[key] = new_endpoint

            # For existing endpoints that weren't marked as modified but match an existing one
            else:
                existing = endpoint_map[key]

                # Just add this file to the used files list
                if "usedInFiles" not in existing:
                    existing["usedInFiles"] = []
                existing_files = set(existing["usedInFiles"])
                new_files = set(new_endpoint.get("usedInFiles", []))
                existing["usedInFiles"] = sorted(
                    list(existing_files.union(new_files))
                )

        return existing_endpoints

    async def analyze_file_for_endpoints(
        self,
        file_path,
        file_content,
        root_dir,
        verbose=False,
        existing_endpoints=None,
    ):
        """
        Analyze a file's content to extract API endpoint information using OpenAI service.
        Takes into account previously identified endpoints to reduce redundancy.

        Returns a list of endpoint dictionaries.
        """
        rel_path = self.get_relative_path(file_path, root_dir)

        if verbose:
            print(f"Analyzing {rel_path}...")

        # Prepare existing endpoints context
        existing_endpoints_json = "[]"
        if existing_endpoints and len(existing_endpoints) > 0:
            # Format existing endpoints for the prompt
            existing_endpoints_json = json.dumps(existing_endpoints, indent=2)

        user_prompt = f"""
        Analyze this React page component to determine what API endpoints it would require:
        File path: {rel_path}
        
        File contents:
        {file_content}
        
        Previously identified endpoints (consider reusing or modifying these when appropriate):
        {existing_endpoints_json}
        """

        try:
            # Use the OpenAIService for completions
            response_text = await self.openai_service.completions(
                user_prompt=user_prompt,
                system_prompt=self.system_prompt,
                response_format={"type": "json_object"},
            )

            result = json.loads(response_text)

            # Add the current file to usedInFiles for each endpoint
            for endpoint in result.get("endpoints", []):
                endpoint["usedInFiles"] = [rel_path]

            return result.get("endpoints", [])

        except Exception as e:
            print(f"Error analyzing {rel_path}: {e}")
            return []

    async def extract_endpoints(
        self,
        root_dir,
        verbose=False,
        max_files=None,
        all_files=False,
        api_files=False,
        react_hooks=False,
        auth_files=False,
    ):
        """
        Extract API endpoint specifications from React codebase.

        Args:
            root_dir (str): Root directory of the React codebase
            verbose (bool, optional): Print verbose output. Defaults to False.
            max_files (int, optional): Maximum number of files to analyze. Defaults to None.
            all_files (bool, optional): Analyze all JS/TS files, not just index files. Defaults to False.
            api_files (bool, optional): Target files with "api" in the name or path. Defaults to False.
            react_hooks (bool, optional): Search for files using useEffect, useQuery, useMutation hooks. Defaults to False.
            auth_files (bool, optional): Search for files containing auth-related keywords. Defaults to False.

        Returns:
            dict: Dictionary with "endpoints" key containing a list of endpoint specifications
        """
        # Find React files to analyze
        react_files = []
        file_type_desc = []

        if api_files:
            # Call async version with await
            api_result = await self.find_react_files(root_dir, api_files=True)
            react_files.extend(api_result)
            file_type_desc.append("API-related files")
        elif all_files:
            # Call async version with await
            all_result = await self.find_react_files(root_dir, all_files=True)
            react_files.extend(all_result)
            file_type_desc.append("React files")
        else:
            # Default: find index files + basic API pattern searches
            # Call async version with await
            default_result = await self.find_react_files(root_dir)
            react_files.extend(default_result)
            file_type_desc.append("index files and API pattern matches")

        # Add files with data fetching hooks if requested
        if react_hooks:
            # Call async version with await
            hook_files = await self.find_react_files(root_dir, react_hooks=True)
            react_files.extend(hook_files)
            file_type_desc.append("hook-using files")

        # Add auth-related files if requested
        if auth_files:
            # Call async version with await
            auth_result = await self.find_react_files(root_dir, auth_files=True)
            react_files.extend(auth_result)
            file_type_desc.append("auth-related files")

        # Remove duplicates
        react_files = list(dict.fromkeys(react_files))

        if verbose:
            print(
                f"Found {len(react_files)} files (from {', '.join(file_type_desc)})"
            )

        # Limit files if max_files is specified
        if max_files:
            react_files = react_files[:max_files]
            if verbose:
                print(f"Limited to {len(react_files)} files")

        # Process each file with progressive endpoint accumulation
        all_endpoints = []

        # Process files concurrently in batches for better performance
        batch_size = 1  # Process 5 files concurrently
        for i in range(0, len(react_files), batch_size):
            batch = react_files[i : i + batch_size]
            batch_tasks = []

            # Create tasks for each file in the batch
            for file_path in batch:
                # Read file content asynchronously
                content = await self.read_file(file_path)

                # Skip empty or unreadable files
                if not content or content.startswith("[ERROR"):
                    continue

                # Create task for endpoint analysis
                task = self.analyze_file_for_endpoints(
                    file_path,
                    content,
                    root_dir,
                    verbose=verbose,
                    existing_endpoints=all_endpoints,
                )
                batch_tasks.append(task)

            # Wait for all tasks in this batch to complete
            batch_results = await asyncio.gather(*batch_tasks)

            # Update endpoints with results from this batch
            for endpoints in batch_results:
                if endpoints and verbose:
                    print(f"  Found {len(endpoints)} endpoints")

                # Update the accumulated endpoints list with new endpoints
                all_endpoints = self.update_endpoints_list(
                    all_endpoints, endpoints
                )

            # Show progress
            if not verbose:
                print(
                    f"Processing files: {min(i+batch_size, len(react_files))}/{len(react_files)}",
                    end="\r",
                )

        # Prepare final output
        result = {"endpoints": all_endpoints}

        # Print a summary if verbose
        if verbose:
            print(f"\nExtracted {len(all_endpoints)} unique endpoints")
            for endpoint in all_endpoints:
                print(
                    f"\n{endpoint.get('method', 'UNKNOWN')} {endpoint['endpointName']}"
                )
                print(
                    f"  Description: {endpoint.get('description', 'No description')}"
                )
                print(f"  Used in {len(endpoint.get('usedInFiles', []))} files")
                print(f"  Auth required: {endpoint.get('authRequired', False)}")
                print(
                    f"  Database required: {endpoint.get('databaseRequired', False)}"
                )
                print(f"  File upload: {endpoint.get('fileUpload', False)}")

        # If no endpoints were found, offer suggestions
        if len(all_endpoints) == 0 and verbose:
            print("\nNo endpoints were detected. You might want to try:")
            print("  - Using all_files=True to scan all JS/TS files")
            print("  - Using api_files=True to target likely API-related files")
            print(
                "  - Using react_hooks=True to find files using data fetching hooks"
            )
            print(
                "  - Using auth_files=True to find authentication-related files"
            )
            print(
                "  - Check if the codebase uses a non-standard API calling pattern"
            )
            print(
                "  - Examine the codebase manually to confirm if it has any API calls"
            )

        return result
