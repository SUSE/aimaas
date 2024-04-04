import re
from typing import Dict, List, Optional

from pydantic import BaseModel, validator, Field, create_model

from ..enums import ModelVariant
from ..models import Schema, AttributeDefinition
from .validators import validate_slug


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


class EntityModelFactory:
    """
    Create pydantic models dynamically based on schema definition
    """
    # Explicit cache dictionary, as caches from functools do not give access to values in time.
    __cache = {}

    @staticmethod
    def clean_fieldname(name: str) -> str:
        """
        Returns modified version of `name` if it shadows member of `pydantic.BaseModel`
        """
        if name in dir(BaseModel):
            return name + '__'
        return name

    @staticmethod
    def clean_modelname(name: str, variant: ModelVariant) -> str:
        parts = re.split("[^a-z0-9]+", name, re.IGNORECASE)
        return "".join(p.capitalize() for p in parts) + variant.name.capitalize()

    @staticmethod
    def fieldtype(attr_def: AttributeDefinition, optional: bool = False) -> tuple:
        """
        Given `AttributeDefinition` returns a type that will be for type annotations in Pydantic
        model
        """
        kwargs = {'description': attr_def.description, 'alias': attr_def.attribute.name}
        type_ = (attr_def.attribute.type  # AttributeDefinition.Attribute.type -> AttrType
                .value.model  # AttrType.value -> Mapping, Mapping.model -> Value model
                .value.property.columns[0].type.python_type)  # get python type of value column in Value child
        if attr_def.list:
            type_ = List[type_]
        if not attr_def.required or optional:
            type_ = Optional[type_]
        return type_, Field(**kwargs)

    def __call__(self, schema: Schema, variant: ModelVariant) -> type:
        key = (schema, variant)

        if key in self.__cache:
            return self.__cache[key]

        if variant is ModelVariant.LIST:
            entity_model = self(schema=schema, variant=ModelVariant.GET)
            model = create_model(
                self.clean_modelname(schema.slug, variant),
                total=(int, Field(description='Total number of entities satisfying conditions')),
                entities=(List[entity_model], Field(description='List of returned entities'))
            )
            self.__cache[key] = model
            return model

        class Config:
            extra = 'forbid'

        attr_fields = {
            self.clean_fieldname(i.attribute.name): self.fieldtype(i,
                                                                   variant != ModelVariant.CREATE)
            for i in schema.attr_defs
        }
        entity_fields = {
            "slug": (Optional[str] if variant is ModelVariant.UPDATE else str,
                     Field(description='Slug of this entity')),
            "name": (Optional[str] if variant is ModelVariant.UPDATE else str,
                     Field(description='Name of this entity'))
        }

        if variant is ModelVariant.GET:
            entity_fields.update({
                'id': (int, Field(description='ID of this entity')),
                'deleted': (bool, Field(description='Indicates whether this entity is marked as '
                                                    'deleted')),
            })

        if variant == ModelVariant.UPDATE:
            entity_fields.update()

        model = create_model(
            self.clean_modelname(schema.slug, variant),
            **entity_fields,
            **attr_fields,
            __config__=Config,
            __validators__={
                'slug_validator': validator('slug', allow_reuse=True)(validate_slug)
            }
        )
        self.__cache[key] = model
        return model
