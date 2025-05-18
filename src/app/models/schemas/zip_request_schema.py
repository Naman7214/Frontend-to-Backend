from pydantic import BaseModel


class ZipPathRequest(BaseModel):
    zip_path: str
