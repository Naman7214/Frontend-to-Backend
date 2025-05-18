import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.app.controllers.fetch_zip_controller import FetchZipController
from src.app.models.schemas.zip_request_schema import ZipPathRequest
from src.app.utils.error_handler import handle_exceptions

router = APIRouter()


@router.post("/fetch-zip")
@handle_exceptions
async def fetch_zip(
    request: Request,
    zip_request: ZipPathRequest,
    controller: FetchZipController = Depends(FetchZipController),
):
    """
    Stream a ZIP file to the client.

    This endpoint streams the generated code as a ZIP file to the frontend,
    allowing users to download the generated codebase.
    """
    return StreamingResponse(
        controller.stream_zip_file(zip_request.zip_path),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={os.path.basename(zip_request.zip_path)}"
        },
    )
