from pydantic import BaseModel


class QueryRequest(BaseModel):
    url: str
