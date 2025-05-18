import os
from fastapi import Depends
from src.app.usecases.clone_usecase.clone_usecase import CloneUseCase
from src.app.usecases.endpoint_usecase.endpoint_usecase import EndpointUseCase
from src.app.usecases.set_priority_usecase import SetPriorityUseCase
from src.app.usecases.database_schema_usecase.database_schema_usecase import DatabaseSchemaUseCase
from src.app.usecases.postman_collection_usecase.postman_collection_usecase import PostmanCollectionUseCase
from src.app.usecases.code_generation_usecase.code_generation_usecase import CodeGenerationUseCase
import time
class BackendCodeGenController:
    """
    Controller for extracting nodes from url.
    """
    def __init__(
        self,
        set_priority_usecase: SetPriorityUseCase = Depends(SetPriorityUseCase),
        clone_usecase: CloneUseCase = Depends(),
        endpoint_usecase: EndpointUseCase = Depends(),
        db_schema_usecase: DatabaseSchemaUseCase = Depends(),
        code_generation_usecase: CodeGenerationUseCase = Depends(CodeGenerationUseCase),
        postman_collection_usecase: PostmanCollectionUseCase = Depends(PostmanCollectionUseCase),
    ):
        self.clone_usecase = clone_usecase
        self.endpoint_usecase = endpoint_usecase
        self.set_priority_usecase = set_priority_usecase
        self.db_schema_usecase = db_schema_usecase
        self.code_generation_usecase = code_generation_usecase
        self.postman_collection_usecase = postman_collection_usecase

    async def code_gen(self, url: str):
        """
        Extract nodes from url and generate codebase.
        """
        # result = await self.clone_usecase.execute(url)
        # repo_path = result["repo_path"]
        # project_uuid = result["project_uuid"]
        repo_path = "Projects/ce526ca7-4e9d-472e-8c3d-5bcb0e8de5fd/podcast"
        project_uuid = "ce526ca7-4e9d-472e-8c3d-5bcb0e8de5fd"
        
        # output_path, output_path_with_sample_payload = await self.endpoint_usecase.execute(repo_path=repo_path, output_path=f"Projects/{project_uuid}/endpoints.json", verbose=True)
        start = time.time()
        _ = await self.db_schema_usecase.execute(json_file_path=f"Projects/{project_uuid}/endpoints.json", repo_path=repo_path)
        end = time.time()
        print(f"Time taken for DB schema usecase: {end - start} seconds")
        # priority_result = await self.set_priority_usecase.set_priority(json_file_path=f"Projects/{project_uuid}/endpoints.json")

        # input_path = f"Projects/{project_uuid}/sorted_endpoints.json"
        # repo_name = os.path.basename(repo_path.rstrip('/'))
        # final_code_path = await self.code_generation_usecase.execute(
        #     input_path=input_path,
        #     project_name=repo_name
        # )
        
        # _ = await self.postman_collection_usecase.execute(output_path_with_sample_payload)

        return "hi"