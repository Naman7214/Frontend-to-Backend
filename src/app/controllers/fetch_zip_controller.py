import asyncio
import os

from fastapi import Depends, HTTPException

from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo


class FetchZipController:
    """
    Controller for fetching and streaming zip files to clients.
    """

    def __init__(self, error_repository: ErrorRepo = Depends(ErrorRepo)):
        self.error_repository = error_repository

    async def stream_zip_file(self, zip_path: str):
        """
        Stream a ZIP file from the specified path.

        Args:
            zip_path: Path to the ZIP file to stream

        Yields:
            Chunks of the ZIP file as bytes
        """
        try:
            # Verify file exists and is a valid zip file
            if not os.path.isfile(zip_path):
                await self.error_repository.insert_error(
                    Error(f"ZIP file not found: {zip_path}")
                )
                raise HTTPException(
                    status_code=404, detail=f"ZIP file not found: {zip_path}"
                )

            if not zip_path.endswith(".zip"):
                await self.error_repository.insert_error(
                    Error(f"Invalid file format. Expected ZIP file: {zip_path}")
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file format. Expected ZIP file: {zip_path}",
                )

            file_size = os.path.getsize(zip_path)

            with open(zip_path, "rb") as file:
                # Use a reasonable chunk size (1MB)
                chunk_size = 1024 * 1024

                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.01)

        except Exception as e:
            error_message = f"Error streaming ZIP file {zip_path}: {str(e)}"
            await self.error_repository.insert_error(Error(error_message))
            raise HTTPException(status_code=500, detail=error_message)
