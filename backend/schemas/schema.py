import re
from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, validator, Field

from ..models import AttrType, AttributeDefinition


class AttrTypeMapping(Enum):
    STR = 'STR'
    BOOL = 'BOOL'
    INT = 'INT'
    FLOAT = 'FLOAT'
    FK = 'FK'
    DT = 'DT'
    DATE = 'DATE'

assert set(AttrType.__members__.keys()) == set(AttrTypeMapping.__members__.keys())

def validate_attribute_name(cls, v: str):
        if v.isidentifier() and re.match('(^_.*)|(.*_$)', v) is None:
            return v
        raise ValueError('Attribute name must be a valid Python identifier and must not start/end with underscore')


class AttributeSchema(BaseModel):
    id: int
    name: str
    type: str

    @validator('type', pre=True)
    def convert_to_str(cls, v):
        if isinstance(v, AttrType) or isinstance(v, AttrTypeMapping):
            return v.name
        elif isinstance(v, str):
            return v
        else:
            raise ValueError('valid types for type field: str, AttrType, AttrTypeMapping')

    validate_attribute_name_ = validator('name', allow_reuse=True)(validate_attribute_name)

    class Config:
        orm_mode = True


class AttributeCreateSchema(BaseModel):
    name: str
    type: AttrTypeMapping

    validate_attribute_name_ = validator('name', allow_reuse=True)(validate_attribute_name)


class AttributeDefinitionBase(BaseModel):
    required: bool
    unique: bool
    list: bool
    key: bool
    description: Optional[str]
    bind_to_schema: Optional[int]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class AttrDefSchema(AttributeDefinitionBase, AttributeCreateSchema):
    @classmethod
    def from_orm(cls, obj: Any):
        if isinstance(obj, AttributeDefinition):
            obj.type = obj.attribute.type.name
            obj.name = obj.attribute.name
            if obj.attribute.type == AttrType.FK:
                obj.bind_to_schema = obj.bound_fk.schema_id
        return super().from_orm(obj)


class AttrDefUpdateSchema(AttributeDefinitionBase):
    name: str
    new_name: Optional[str]

    validate_attribute_name_ = validator('name', allow_reuse=True)(validate_attribute_name)


def validate_slug(cls, slug: str):
    if slug is None:
        return slug
    if re.match('^[a-zA-Z]+[0-9]*(-[a-zA-Z0-9]+)*$', slug) is None:
        raise ValueError(f'`{slug}` is invalid value for slug field')
    return slug


class SchemaBaseSchema(BaseModel):
    id: int
    name: str
    slug: str
    deleted: bool

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class SchemaCreateSchema(BaseModel):
    name: str
    slug: str
    reviewable: bool = False
    attributes: List[AttrDefSchema]

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)


class SchemaUpdateSchema(BaseModel):
    name: Optional[str]
    slug: Optional[str]
    reviewable: Optional[bool]

    update_attributes: List[AttrDefUpdateSchema] = []
    add_attributes: List[AttrDefSchema] = []
    delete_attributes: List[str] = []

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)


class SchemaForListSchema(SchemaBaseSchema):
    pass


class SchemaDetailSchema(SchemaBaseSchema):
    deleted: bool
    reviewable: bool
    attr_defs: List[AttrDefSchema] = Field(alias='attributes')