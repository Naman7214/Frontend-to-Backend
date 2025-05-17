from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from src.app.models.schemas.query_schema import QueryRequest
from src.app.controllers.backend_code_gen_controller import (
    BackendCodeGenController,
)
from src.app.utils.error_handler import handle_exceptions

router = APIRouter()


@router.post("/backend-code-gen")
@handle_exceptions
async def backend_code_gen(
    query: QueryRequest,
    controller: BackendCodeGenController = Depends(BackendCodeGenController),
):
    """
    Route for extracting nodes from url.
    """
    result = await controller.code_gen(query.url)

    return JSONResponse(
        content={
            "data": result,
            "statuscode": 200,
            "detail": "Nodes extracted successfully.",
            "error": "",
        },
        status_code=status.HTTP_200_OK,
    )
