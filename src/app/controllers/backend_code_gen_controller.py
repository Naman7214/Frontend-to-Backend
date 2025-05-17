import json

from fastapi import Depends
from src.app.usecases.clone_usecase.clone_usecase import CloneUseCase
from src.app.usecases.endpoint_usecase.endpoint_usecase import EndpointUseCase
import json
from src.app.usecases.set_priority_usecase import SetPriorityUseCase
from src.app.usecases.database_schema_usecase.database_schema_usecase import DatabaseSchemaUseCase

class BackendCodeGenController:
    """
    Controller for extracting nodes from url.
    """

    def __init__(
        self, set_priority_usecase: SetPriorityUseCase = Depends(SetPriorityUseCase), clone_usecase: CloneUseCase = Depends(), endpoint_usecase: EndpointUseCase = Depends()
    ):
        self.clone_usecase = clone_usecase
        self.endpoint_usecase = endpoint_usecase
        self.set_priority_usecase = set_priority_usecase

        # self.usecase = usecase
        pass

    async def code_gen(self, url: str):
        """
        Extract nodes from url.
        """
        # with open("temp/temp.json", "r") as f:
        #     data = json.load(f)

        # response = await self.set_priority_usecase.set_priority(data)
        result = await self.clone_usecase.execute(url)
        repo_path = result["repo_path"]
        project_uuid = result["project_uuid"]
        # Call the endpoint use case to extract endpoints
        output_path = await self.endpoint_usecase.execute(repo_path=repo_path, output_path=f"Projects/{project_uuid}/endpoints.json", verbose=True)
        print(f"Output path: {output_path}")
        return f"Code generation logic for URL: {url}"
        # return await self.usecase.execute()
