from fastapi import Depends

# from src.app.usecases.nodes_extraction_usecase import NodesExtractionUseCase


class BackendCodeGenController:
    """
    Controller for extracting nodes from url.
    """

    # def __init__(
    #     # self, usecase: NodesExtractionUseCase = Depends(NodesExtractionUseCase)
    # ):
    #     # self.usecase = usecase
    #     pass

    async def code_gen(self, url: str):
        """
        Extract nodes from url.
        """
        return f"Code generation logic for URL: {url}"
        # return await self.usecase.execute()
