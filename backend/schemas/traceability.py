from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field, validator

from ..models import ChangeObject, ChangeStatus, ChangeType, User
from .schema import AttrDefSchema, AttrDefUpdateSchema, SchemaBaseSchema


class ChangeRequestSchema(BaseModel):
    id: Optional[int]
    created_at: datetime
    reviewed_at: Optional[datetime]
    created_by: str
    reviewed_by: Optional[str]
    status: ChangeStatus
    comment: Optional[str]

    class Config:
        orm_mode = True

    @validator('created_by', 'reviewed_by', pre=True)
    def convert_to_str(cls, v):
        if isinstance(v, User):
            return v.username
        return v

class ReviewResult(Enum):
    APPROVE = 'APPROVE'
    DECLINE = 'DECLINE'


class ChangeReviewSchema(BaseModel):
    result: ReviewResult
    change_object: ChangeObject
    change_type: ChangeType
    comment: Optional[str]
    

class ChangedEntitySchema(BaseModel):
    slug: str
    name: str
    schema_slug: str = Field(alias='schema')


class EntityChangeSchema(BaseModel):
    new: Optional[Union[Any, list[Any]]]
    old: Optional[Any]
    current: Optional[Any]


class EntityChangeDetailSchema(ChangeRequestSchema):
    entity: ChangedEntitySchema
    changes: dict[str, EntityChangeSchema]


class SchemaChangesSchema(BaseModel):
    name: Optional[Dict[str, str]]
    slug: Optional[Dict[str, str]]
    reviewable: Optional[Dict[str, bool]]
    deleted: Optional[Dict[str, bool]]
    add: Optional[List[AttrDefSchema]]
    update: Optional[List[AttrDefUpdateSchema]]
    delete: Optional[List[str]]


class SchemaChangeDetailSchema(ChangeRequestSchema):
    schema_: SchemaBaseSchema = Field(alias='schema')
    changes: SchemaChangesSchema