from typing import Any, List, Optional

from pydantic import BaseModel

from .models import AttrType


class AttributeCreateSchema(BaseModel):
    name: str
    type: AttrType

class AttributeDefinitionSchema(BaseModel):
    attr_id: int
    required: bool
    unique: bool
    list: bool
    key: bool
    description: Optional[str]
    bind_to_schema: Optional[int]

class AttributeDefinitionUpdateSchema(AttributeDefinitionSchema):
    id: int

class SchemaCreateSchema(BaseModel):
    name: str
    slug: str
    attributes: List[AttributeDefinitionSchema]


class SchemaUpdateSchema(BaseModel):
    name: str
    slug: str

    update_attributes: List[AttributeDefinitionUpdateSchema]
    add_attributes: List[AttributeDefinitionSchema]