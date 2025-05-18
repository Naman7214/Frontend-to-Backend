import os
import json
import asyncio
from datetime import datetime
from fastapi import Depends, Request
from src.app.usecases.clone_usecase.clone_usecase import CloneUseCase
from src.app.usecases.endpoint_usecase.endpoint_usecase import EndpointUseCase
from src.app.usecases.set_priority_usecase.set_priority_usecase import SetPriorityUseCase
from src.app.usecases.database_schema_usecase.database_schema_usecase import DatabaseSchemaUseCase
from src.app.usecases.postman_collection_usecase.postman_collection_usecase import PostmanCollectionUseCase
from src.app.usecases.code_generation_usecase.code_generation_usecase import CodeGenerationUseCase
from src.app.usecases.code_contructor_usecase.code_constructor_usecase import CodeConstructorUseCase
from src.app.repositories.error_repository import ErrorRepo
from src.app.models.domain.error import Error
import asyncio
class BackendCodeGenController:
    """
    Controller for extracting nodes from url.
    """
    def __init__(
        self,
        set_priority_usecase: SetPriorityUseCase = Depends(SetPriorityUseCase),
        clone_usecase: CloneUseCase = Depends(CloneUseCase),
        endpoint_usecase: EndpointUseCase = Depends(EndpointUseCase),
        db_schema_usecase: DatabaseSchemaUseCase = Depends(DatabaseSchemaUseCase),
        code_generation_usecase: CodeGenerationUseCase = Depends(CodeGenerationUseCase),
        postman_collection_usecase: PostmanCollectionUseCase = Depends(PostmanCollectionUseCase),
        error_repository: ErrorRepo = Depends(ErrorRepo),
        code_constructor_usecase: CodeConstructorUseCase = Depends(CodeConstructorUseCase)
    ):
        self.clone_usecase = clone_usecase
        self.endpoint_usecase = endpoint_usecase
        self.set_priority_usecase = set_priority_usecase
        self.db_schema_usecase = db_schema_usecase
        self.code_generation_usecase = code_generation_usecase
        self.postman_collection_usecase = postman_collection_usecase
        self.error_repository = error_repository
        self.code_constructor_usecase = code_constructor_usecase

    async def code_gen(self, url: str):
        """
        Extract nodes from url and generate codebase.
        """
        result = await self.clone_usecase.execute(url)
        repo_path = result["repo_path"]
        project_uuid = result["project_uuid"]
        
        output_path, output_path_with_sample_payload, simplified_end_points = await self.endpoint_usecase.execute(repo_path=repo_path, output_path=f"Projects/{project_uuid}/endpoints.json", verbose=True)

        # Run database schema generation and priority setting in parallel
        db_schema_task = asyncio.create_task(
            self.db_schema_usecase.execute(json_file_path=f"Projects/{project_uuid}/endpoints.json", repo_path=repo_path)
        )
        
        priority_task = asyncio.create_task(
            self.set_priority_usecase.set_priority(json_file_path=f"Projects/{project_uuid}/endpoints.json")
        )
        
        # Wait for both tasks to complete
        _ = await db_schema_task
        priority_result = await priority_task

        # Run code generation and postman collection generation in parallel
        input_path = f"Projects/{project_uuid}/sorted_endpoints.json"
        repo_name = os.path.basename(repo_path.rstrip('/'))
        
        code_gen_task = asyncio.create_task(
            self.code_generation_usecase.execute(
                input_path=input_path,
                project_name=repo_name
            )
        )
        
        postman_task = asyncio.create_task(
            self.postman_collection_usecase.execute(output_path_with_sample_payload)
        )
        
        # Wait for both tasks to complete
        final_code_path = await code_gen_task
        _ = await postman_task
        # Generate code constructor
        code_json_path = f"Projects/{project_uuid}/final_code.json"
        zip_path = await self.code_constructor_usecase.execute(code_json_path)
        return {
            "project_uuid": project_uuid,
            "repo_name": repo_name,
            "final_code_path": final_code_path,
            "zip_path": zip_path
        }
        
    async def stream_code_gen(self, url: str):
        """
        Stream the code generation process step by step.
        
        Args:
            url: GitHub repository URL to generate code from
            
        Yields:
            Tuples of (event_type, data) for streaming to the client
        """
        try:
            self.start_time = datetime.utcnow()
            yield ("status", "Starting code generation process")
            
            # Clone repository
            yield ("status", "Cloning repository...")
            result = await self.clone_usecase.execute(url)
            repo_path = result["repo_path"]
            project_uuid = result["project_uuid"]
            repo_name = os.path.basename(repo_path.rstrip('/'))
            yield ("status", f"Repository cloned successfully: {repo_name}")
            
            # Extract endpoints
            yield ("status", "Extracting API endpoints...")
            output_path, output_path_with_sample_payload, simplified_end_points = await self.endpoint_usecase.execute(
                repo_path=repo_path, 
                output_path=f"Projects/{project_uuid}/endpoints.json",
                verbose=True
            )
            # Send status and endpoints data
            yield ("status", "API endpoints extracted successfully")
            yield ("endpoints", simplified_end_points)
            
            # Generate database schema and set priorities in parallel
            yield ("status", "Generating database schema and setting priorities in parallel...")
            
            db_schema_task = asyncio.create_task(
                self.db_schema_usecase.execute(
                    json_file_path=f"Projects/{project_uuid}/endpoints.json", 
                    repo_path=repo_path
                )
            )
            
            priority_task = asyncio.create_task(
                self.set_priority_usecase.set_priority(
                    json_file_path=f"Projects/{project_uuid}/endpoints.json"
                )
            )
            
            # Wait for both tasks to complete
            schema_result = await db_schema_task
            yield ("status", "Database schema generated successfully")
            
            priority_result = await priority_task
            yield ("status", "API endpoints prioritized successfully")
            
            # Generate code and Postman collection in parallel
            yield ("status", "Generating backend code and Postman collection in parallel...")
            input_path = f"Projects/{project_uuid}/sorted_endpoints.json"
            
            code_gen_task = asyncio.create_task(
                self.code_generation_usecase.execute(
                    input_path=input_path,
                    project_name=repo_name
                )
            )
            
            postman_task = asyncio.create_task(
                self.postman_collection_usecase.execute(output_path_with_sample_payload)
            )
            
            # Wait for both tasks to complete
            final_code_path = await code_gen_task
            yield ("status", "Backend code generated successfully")
            
            postman_result = await postman_task
            yield ("status", "Postman collection generated successfully")
            
            # Generate code constructor
            yield ("status", "Constructing and zipping final API codebase...")
            code_json_path = f"Projects/{project_uuid}/final_code.json"
            zip_path = await self.code_constructor_usecase.execute(code_json_path)
            yield ("status", "API codebase constructed and zipped successfully")
            
            # Return completion data
            yield (
                "completed",
                {
                    "project_uuid": project_uuid,
                    "repo_name": repo_name,
                    "final_code_path": final_code_path,
                    "zip_path": zip_path
                }
            )
        
        except Exception as e:
            await self.error_repository.insert_error(Error(str(e)))
            yield ("error", f"Error in stream_code_gen: {str(e)}")
    
    async def format_streaming_events(self, query: str, request=None):
        """
        Process code generation with streaming and format as SSE events.

        Args:
            query: GitHub repository URL string
            request: Optional FastAPI request object to check for disconnection

        Yields:
            Formatted SSE event strings
        """
        try:
            # Start the stream with a message
            yield "event: message_start\n"
            yield f"data: {json.dumps({'type': 'message_start', 'message': 'Starting code generation'})}\n\n"

            # Process the workflow with streaming updates
            async for event_type, content in self.stream_code_gen(query):
                # Check for client disconnection if request object provided
                if request and await request.is_disconnected():
                    break

                # Format the event based on type
                if event_type == "status":
                    yield f"event: status\n"
                    yield f"data: {json.dumps({'status': content})}\n\n"
                
                elif event_type == "endpoints":
                    yield f"event: endpoints\n"
                    yield f"data: {json.dumps({'endpoints': content})}\n\n"

                elif event_type == "error":
                    yield f"event: error\n"
                    yield f"data: {json.dumps({'error': content})}\n\n"

                elif event_type == "completed":
                    yield f"event: completed\n"
                    yield f"data: {json.dumps({'result': content})}\n\n"

                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)

            # End the stream
            yield f"event: message_stop\n"
            yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

        except Exception as e:
            await self.error_repository.insert_error(
                Error(f"Error in event formatting: {str(e)}")
            )
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield f"event: message_stop\n"
            yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"