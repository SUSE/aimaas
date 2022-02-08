import typing

from pydantic import BaseModel


class FilterModel(BaseModel):
    name: str
    description: str


class InfoModel(BaseModel):
    version: str
    filters: typing.List[FilterModel]
    filters_per_type: typing.Dict[str, typing.List[str]]
