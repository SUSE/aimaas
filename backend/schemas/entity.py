import re
from typing import Dict, List, Union

from pydantic import BaseModel, validator, Field

from ..models import Schema


def validate_slug(cls, slug: str):
    if slug is None:
        return slug
    if re.match('^[a-zA-Z]+[0-9]*(-[a-zA-Z0-9]+)*$', slug) is None:
        raise ValueError(f'`{slug}` is invalid value for slug field')
    return slug


class EntityBaseSchema(BaseModel):
    id: int
    slug: str
    name: str
    deleted: bool

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)
    
    class Config:
        orm_mode = True

    
class EntityByIdSchema(EntityBaseSchema):
    schema_slug: str = Field(alias='schema')

    class Config:
        orm_mode = True

    @validator('schema_slug', pre=True)
    def convert_to_str(cls, v):
        if isinstance(v, Schema):
            return v.slug
        else:
            return v


class EntityListSchema(BaseModel):
    total: int
    entities: List[dict]


class FilterFields(BaseModel):
    operators: Dict[str, List[str]]
    fields: Dict[str, Dict[str, str]]
