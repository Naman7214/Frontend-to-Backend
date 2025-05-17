from fastapi import Depends
import json
from src.app.usecases.set_priority_usecase import SetPriorityUseCase


class BackendCodeGenController:
    """
    Controller for extracting nodes from url.
    """

    def __init__(
        self, set_priority_usecase: SetPriorityUseCase = Depends(SetPriorityUseCase)
    ):
        self.set_priority_usecase = set_priority_usecase

    async def code_gen(self, url: str):
        """
        Extract nodes from url.
        """
        with open("temp/temp.json", "r") as f:
            data = json.load(f)

        response = await self.set_priority_usecase.set_priority(data)
        return f"Code generation logic for URL: {url}"
        # return await self.usecase.execute()
