from datetime import datetime
from typing import List, Optional, Union, Any

from pydantic import BaseModel, Field, validator

from ..auth.models import User
from .schema import SchemaBaseSchema
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


class ChangeSchema(BaseModel):
    new: Optional[Union[Any, List[Any]]]
    old: Optional[Union[Any, List[Any]]]
    current: Optional[Union[Any, List[Any]]]


class EntityChangeDetailSchema(ChangeRequestSchema):
    entity: ChangedEntitySchema
    changes: dict[str, ChangeSchema]


class SchemaChangeDetailSchema(ChangeRequestSchema):
    schema_: Optional[SchemaBaseSchema] = Field(alias='schema')
    changes: dict[str, ChangeSchema]
