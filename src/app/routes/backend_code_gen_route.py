from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.app.controllers.backend_code_gen_controller import (
    BackendCodeGenController,
)
from src.app.models.schemas.query_schema import QueryRequest
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


@router.post("/stream-code-gen")
async def stream_workflow(
    request: Request,
    query: QueryRequest,
    backend_code_gen_controller: BackendCodeGenController = Depends(
        BackendCodeGenController
    ),
):
    """Stream workflow generation process to the client."""
    return StreamingResponse(
        backend_code_gen_controller.format_streaming_events(query.url, request),
        media_type="text/event-stream",
    )
