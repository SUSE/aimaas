from typing import List, Optional, Union

from pydantic import BaseModel

from .models import AttrType


class AttributeCreateSchema(BaseModel):
    name: str
    type: AttrType


class AttributeDefinitionBase(BaseModel):
    required: bool
    unique: bool
    list: bool
    key: bool
    description: Optional[str]
    bind_to_schema: Optional[int]


class AttrDefSchema(AttributeDefinitionBase):
    attr_id: int


class AttrDefWithAttrDataSchema(AttributeDefinitionBase, AttributeCreateSchema):
    pass


class AttributeDefinitionUpdateSchema(AttrDefSchema):
    id: int


class SchemaCreateSchema(BaseModel):
    name: str
    slug: str
    attributes: List[Union[AttrDefSchema, AttrDefWithAttrDataSchema]]


class SchemaUpdateSchema(BaseModel):
    name: str
    slug: str

    update_attributes: List[AttributeDefinitionUpdateSchema]
    add_attributes: List[Union[AttrDefSchema, AttrDefWithAttrDataSchema]]