import asyncio
import glob
import json
import os
import re
import traceback

import aiofiles
from fastapi import Depends

from src.app.models.domain.error import Error
from src.app.prompts.endpoint_prompt import ENDPOINT_PROMPT_SYSTEM_PROMPT
from src.app.repositories.error_repository import ErrorRepo
from src.app.services.openai_service import OpenAIService


class EndpointHelper:
    def __init__(
        self, 
        openai_service: OpenAIService = Depends(OpenAIService),
        error_repo: ErrorRepo = Depends(ErrorRepo)
    ) -> None:
        self.openai_service = openai_service
        self.error_repo = error_repo
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
                    # Log subprocess error but continue with fallback
                    error_msg = f"EndpointHelper.find_files_with_grep: Subprocess grep failed for pattern '{pattern}': {str(e)}"
                    await self.error_repo.insert_error(Error(error_msg))
                    
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
                            except Exception as file_error:
                                # Log file reading errors
                                error_msg = f"EndpointHelper.find_files_with_grep: Failed to read file {file_path}: {str(file_error)}"
                                await self.error_repo.insert_error(Error(error_msg))
            except Exception as outer_e:
                error_msg = f"EndpointHelper.find_files_with_grep: Critical error searching for pattern '{pattern}': {str(outer_e)}\n{traceback.format_exc()}"
                await self.error_repo.insert_error(Error(error_msg))

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
        try:
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

            # Collect files from all patterns
            try:
                for pattern in patterns:
                    result_files.extend(glob.glob(pattern, recursive=True))
            except Exception as glob_error:
                error_msg = f"EndpointHelper.find_react_files: Error in glob pattern search: {str(glob_error)}\n{traceback.format_exc()}"
                await self.error_repo.insert_error(Error(error_msg))

            # Always perform basic API-related searches even in normal execution
            try:
                api_fetch_patterns = [
                    "useEffect",
                    "useQuery",
                    "useMutation",
                    "useState",
                ]
                api_files = await self.find_files_with_grep(
                    root_dir, api_fetch_patterns
                )
                result_files.extend(api_files)
            except Exception as api_search_error:
                error_msg = f"EndpointHelper.find_react_files: Error in API pattern search: {str(api_search_error)}\n{traceback.format_exc()}"
                await self.error_repo.insert_error(Error(error_msg))

            # Add files containing React hooks for data fetching if explicitly requested
            if react_hooks:
                try:
                    hook_patterns = [
                        "useEffect",
                        "useQuery",
                        "useMutation",
                        "useApi",
                        "useFetch",
                        "useHttp",
                        "useRequest",
                    ]
                    hook_files = await self.find_files_with_grep(
                        root_dir, hook_patterns
                    )
                    result_files.extend(hook_files)
                except Exception as hook_search_error:
                    error_msg = f"EndpointHelper.find_react_files: Error in hook pattern search: {str(hook_search_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))

            # Add files with auth-related keywords if explicitly requested
            if auth_files:
                try:
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
                    auth_files = await self.find_files_with_grep(
                        root_dir, auth_patterns
                    )
                    result_files.extend(auth_files)
                except Exception as auth_search_error:
                    error_msg = f"EndpointHelper.find_react_files: Error in auth pattern search: {str(auth_search_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))

            # Remove duplicates while preserving order
            seen = set()
            unique_files = []
            for file in result_files:
                if file not in seen:
                    seen.add(file)
                    unique_files.append(file)

            return unique_files
            
        except Exception as e:
            error_msg = f"EndpointHelper.find_react_files: Critical error finding React files: {str(e)}\n{traceback.format_exc()}"
            await self.error_repo.insert_error(Error(error_msg))
            # Return empty list instead of raising to allow partial results
            return []

    async def read_file(self, file_path):
        """Read a file's contents as text (async version)."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except UnicodeDecodeError as ude:
            error_msg = f"EndpointHelper.read_file: Unicode decode error in file {file_path}: {str(ude)}"
            await self.error_repo.insert_error(Error(error_msg))
            # Try with a different encoding as fallback
            try:
                async with aiofiles.open(file_path, "r", encoding="latin-1") as f:
                    return await f.read()
            except Exception as fallback_error:
                error_msg = f"EndpointHelper.read_file: Fallback encoding also failed for {file_path}: {str(fallback_error)}"
                await self.error_repo.insert_error(Error(error_msg))
                return f"[ERROR: Could not read file with any encoding]"
        except FileNotFoundError as fnf:
            error_msg = f"EndpointHelper.read_file: File not found {file_path}: {str(fnf)}"
            await self.error_repo.insert_error(Error(error_msg))
            return f"[ERROR: File not found]"
        except PermissionError as pe:
            error_msg = f"EndpointHelper.read_file: Permission denied for file {file_path}: {str(pe)}"
            await self.error_repo.insert_error(Error(error_msg))
            return f"[ERROR: Permission denied]"
        except Exception as e:
            error_msg = f"EndpointHelper.read_file: Unexpected error reading {file_path}: {str(e)}\n{traceback.format_exc()}"
            await self.error_repo.insert_error(Error(error_msg))
            return f"[ERROR: Could not read file: {str(e)}]"

    def get_relative_path(self, file_path, root_dir):
        """Convert absolute path to relative path from root_dir."""
        try:
            abs_root = os.path.abspath(root_dir)
            abs_file = os.path.abspath(file_path)
            return os.path.relpath(abs_file, abs_root)
        except ValueError as ve:
            # This can happen if paths are on different drives (Windows)
            error_msg = f"EndpointHelper.get_relative_path: Value error for paths - file: {file_path}, root: {root_dir}: {str(ve)}"
            # Cannot await here since this method isn't async
            # Return the original path as fallback
            return file_path

    def update_endpoints_list(self, existing_endpoints, new_endpoints):
        """
        Update the existing endpoints list with new endpoints, merging where appropriate.
        Handles both modified endpoints and entirely new endpoints.
        """
        try:
            # Create a lookup map for existing endpoints by name and method
            endpoint_map = {}
            for endpoint in existing_endpoints:
                try:
                    key = f"{endpoint['endpointName']}:{endpoint.get('method', 'UNKNOWN')}"
                    endpoint_map[key] = endpoint
                except KeyError as ke:
                    # This should not log to MongoDB as it's not an async method
                    # Just handle the error gracefully and continue
                    continue
                except Exception as e:
                    # Unexpected error in endpoint processing
                    # Continue to process other endpoints
                    continue

            # Process each new endpoint
            for new_endpoint in new_endpoints:
                try:
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
                except KeyError as ke:
                    # Missing required key in endpoint data
                    # Skip this endpoint but continue processing others
                    continue
                except Exception as e:
                    # Unexpected error in endpoint processing
                    # Skip this endpoint but continue processing others
                    continue

            return existing_endpoints
            
        except Exception as e:
            # Critical error in endpoint list update
            # Return original list as fallback
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
        try:
            rel_path = self.get_relative_path(file_path, root_dir)

            if verbose:
                print(f"Analyzing {rel_path}...")

            # Prepare existing endpoints context
            existing_endpoints_json = "[]"
            if existing_endpoints and len(existing_endpoints) > 0:
                # Format existing endpoints for the prompt
                try:
                    existing_endpoints_json = json.dumps(existing_endpoints, indent=2)
                except Exception as json_error:
                    error_msg = f"EndpointHelper.analyze_file_for_endpoints: Error serializing existing endpoints: {str(json_error)}"
                    await self.error_repo.insert_error(Error(error_msg))
                    existing_endpoints_json = "[]"

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

            except json.JSONDecodeError as json_error:
                error_msg = f"EndpointHelper.analyze_file_for_endpoints: JSON decode error for file {rel_path}: {str(json_error)}\nResponse text: {response_text[:200]}..."
                await self.error_repo.insert_error(Error(error_msg))
                return []
            except Exception as service_error:
                error_msg = f"EndpointHelper.analyze_file_for_endpoints: OpenAI service error for file {rel_path}: {str(service_error)}\n{traceback.format_exc()}"
                await self.error_repo.insert_error(Error(error_msg))
                return []

        except Exception as e:
            error_msg = f"EndpointHelper.analyze_file_for_endpoints: Critical error analyzing file {file_path}: {str(e)}\n{traceback.format_exc()}"
            await self.error_repo.insert_error(Error(error_msg))
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
        try:
            # Find React files to analyze
            react_files = []
            file_type_desc = []

            if api_files:
                try:
                    # Call async version with await
                    api_result = await self.find_react_files(root_dir, api_files=True)
                    react_files.extend(api_result)
                    file_type_desc.append("API-related files")
                except Exception as api_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error finding API files: {str(api_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))
            elif all_files:
                try:
                    # Call async version with await
                    all_result = await self.find_react_files(root_dir, all_files=True)
                    react_files.extend(all_result)
                    file_type_desc.append("React files")
                except Exception as all_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error finding all files: {str(all_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))
            else:
                try:
                    # Default: find index files + basic API pattern searches
                    # Call async version with await
                    default_result = await self.find_react_files(root_dir)
                    react_files.extend(default_result)
                    file_type_desc.append("index files and API pattern matches")
                except Exception as default_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error finding default files: {str(default_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))

            # Add files with data fetching hooks if requested
            if react_hooks:
                try:
                    # Call async version with await
                    hook_files = await self.find_react_files(root_dir, react_hooks=True)
                    react_files.extend(hook_files)
                    file_type_desc.append("hook-using files")
                except Exception as hook_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error finding hook files: {str(hook_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))

            # Add auth-related files if requested
            if auth_files:
                try:
                    # Call async version with await
                    auth_result = await self.find_react_files(root_dir, auth_files=True)
                    react_files.extend(auth_result)
                    file_type_desc.append("auth-related files")
                except Exception as auth_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error finding auth files: {str(auth_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))

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
            batch_size = 1  # Process 1 file at a time for better error isolation
            for i in range(0, len(react_files), batch_size):
                try:
                    batch = react_files[i : i + batch_size]
                    batch_tasks = []

                    # Create tasks for each file in the batch
                    for file_path in batch:
                        try:
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
                        except Exception as file_error:
                            error_msg = f"EndpointHelper.extract_endpoints: Error processing file {file_path}: {str(file_error)}\n{traceback.format_exc()}"
                            await self.error_repo.insert_error(Error(error_msg))
                            continue

                    # Wait for all tasks in this batch to complete
                    try:
                        batch_results = await asyncio.gather(*batch_tasks)
                    except Exception as gather_error:
                        error_msg = f"EndpointHelper.extract_endpoints: Error gathering batch results: {str(gather_error)}\n{traceback.format_exc()}"
                        await self.error_repo.insert_error(Error(error_msg))
                        # Use empty list to continue processing
                        batch_results = []

                    # Update endpoints with results from this batch
                    for endpoints in batch_results:
                        if endpoints and verbose:
                            print(f"  Found {len(endpoints)} endpoints")

                        try:
                            # Update the accumulated endpoints list with new endpoints
                            all_endpoints = self.update_endpoints_list(
                                all_endpoints, endpoints
                            )
                        except Exception as update_error:
                            error_msg = f"EndpointHelper.extract_endpoints: Error updating endpoints list: {str(update_error)}\n{traceback.format_exc()}"
                            await self.error_repo.insert_error(Error(error_msg))

                    # Show progress
                    if not verbose:
                        print(
                            f"Processing files: {min(i+batch_size, len(react_files))}/{len(react_files)}",
                            end="\r",
                        )
                except Exception as batch_error:
                    error_msg = f"EndpointHelper.extract_endpoints: Error processing batch at index {i}: {str(batch_error)}\n{traceback.format_exc()}"
                    await self.error_repo.insert_error(Error(error_msg))
                    continue

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
        except Exception as e:
            error_msg = f"EndpointHelper.extract_endpoints: Critical error extracting endpoints: {str(e)}\n{traceback.format_exc()}"
            await self.error_repo.insert_error(Error(error_msg))
            # Return empty result to avoid breaking caller
            return {"endpoints": []}
