import re
from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel, validator, Field, root_validator

from ..models import AttrType, AttributeDefinition
from .validators import validate_slug


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
    raise ValueError(
        'Attribute name must be a valid Python identifier and must not start/end with underscore')


class AttributeCreateSchema(BaseModel):
    name: str
    type: AttrTypeMapping

    validate_attribute_name_ = validator('name', allow_reuse=True)(validate_attribute_name)


class AttributeDefinitionBase(BaseModel):
    required: bool
    unique: bool
    list: bool
    key: bool
    description: Optional[str] = None
    bound_schema_id: Optional[int] = None
    id: Optional[int] = None

    @root_validator(pre=True)
    def check_type_and_bound_id(cls, values):
        if values.get("type", None) in (AttrTypeMapping.FK, 'FK') \
                and values.get("bound_schema_id") is None:
            raise ValueError("Attribute type FK must be bound to a specific schema")

        return values

    @validator("description", pre=True)
    def check_description_length(cls, value):
        if value and len(value) > 1000:
            raise ValueError("Description exceeds the maximum character length of 1000.")

        return value

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class AttrDefSchema(AttributeDefinitionBase, AttributeCreateSchema):
    @classmethod
    def from_orm(cls, obj: Any):
        if isinstance(obj, AttributeDefinition):
            obj.type = obj.attribute.type.name
            obj.name = obj.attribute.name
        return super().from_orm(obj)


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
    attributes: List[AttrDefSchema] = []

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)


class SchemaBaseSchema(BaseModel):
    id: int
    name: str
    slug: str
    deleted: bool

    slug_validator = validator('slug', allow_reuse=True)(validate_slug)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class SchemaForListSchema(SchemaBaseSchema):
    pass


class SchemaDetailSchema(SchemaBaseSchema):
    deleted: bool
    reviewable: bool
    attr_defs: List[AttrDefSchema] = Field(alias='attributes')


class AttributeSchema(BaseModel):
    id: int
    name: str
    type: str

    validate_attribute_name_ = validator('name', allow_reuse=True)(validate_attribute_name)

    @validator('type', pre=True)
    def convert_to_str(cls, v):
        if isinstance(v, AttrType) or isinstance(v, AttrTypeMapping):
            return v.name
        elif isinstance(v, str):
            return v
        else:
            raise ValueError('valid types for type field: str, AttrType, AttrTypeMapping')

    class Config:
        orm_mode = True
