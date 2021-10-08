from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, validator

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

    @validator('type', pre=True)
    def convert_from_attrtype(cls, v):
        if isinstance(v, AttrTypeMapping):
            return v
        elif isinstance(v, AttrType):
            try:
                return AttrTypeMapping[v.name]
            except KeyError:
                keys = AttrType.__members__.keys()
                raise ValueError(f'value is not a valid enumeration member; permitted: {", ".join(keys)}')

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