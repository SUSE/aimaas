from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field, validator

from ..auth.models import User
from .schema import AttrDefSchema, AttrDefUpdateSchema, SchemaBaseSchema
from ..traceability.enum import EditableObjectType, ChangeStatus, ChangeType, ReviewResult


class ChangeRequestSchema(BaseModel):
    id: Optional[int]
    created_at: datetime
    reviewed_at: Optional[datetime]
    created_by: str
    reviewed_by: Optional[str]
    status: ChangeStatus
    comment: Optional[str]
    object_type: EditableObjectType
    change_type: ChangeType

    class Config:
        orm_mode = True

    @validator('created_by', 'reviewed_by', pre=True)
    def convert_to_str(cls, v):
        if isinstance(v, User):
            return v.username
        return v

class SchemaChangeRequestSchema(BaseModel):
    schema_changes: List[ChangeRequestSchema]
    pending_entity_requests: List[ChangeRequestSchema]


class ChangeReviewSchema(BaseModel):
    result: ReviewResult
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
    name: Optional[Dict[str, Optional[str]]]
    slug: Optional[Dict[str, Optional[str]]]
    reviewable: Optional[Dict[str, Optional[bool]]]
    deleted: Optional[Dict[str, bool]]
    add: Optional[List[AttrDefSchema]]
    update: Optional[List[AttrDefUpdateSchema]]
    delete: Optional[List[str]]


class SchemaChangeDetailSchema(ChangeRequestSchema):
    schema_: SchemaBaseSchema = Field(alias='schema')
    changes: SchemaChangesSchema