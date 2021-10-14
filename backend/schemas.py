from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel

from .models import AttrType

class AttrTypeMapping(Enum):
    STR = 'STR'
    BOOL = 'BOOL'
    INT = 'INT'
    FLOAT = 'FLOAT'
    FK = 'FK'
    DT = 'DT'

assert set(AttrType.__members__.keys()) == set(AttrTypeMapping.__members__.keys())


class AttributeCreateSchema(BaseModel):
    name: str
    type: AttrTypeMapping


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


class AttributeDefinitionUpdateSchema(AttributeDefinitionBase):
    attr_def_id: int


class AttributeDefinitionUpdateWithNameSchema(AttributeDefinitionBase):
    name: str


class SchemaCreateSchema(BaseModel):
    name: str
    slug: str
    attributes: List[Union[AttrDefSchema, AttrDefWithAttrDataSchema]]


class SchemaUpdateSchema(BaseModel):
    name: str
    slug: str

    update_attributes: List[Union[AttributeDefinitionUpdateSchema, AttributeDefinitionUpdateWithNameSchema]]
    add_attributes: List[Union[AttrDefSchema, AttrDefWithAttrDataSchema]]