from pydantic import BaseModel


class InfoModel(BaseModel):
    version: str
