from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field

from ..models import ChangeObject, ChangeStatus, ChangeType
from .schema import AttrDefSchema, AttrDefUpdateSchema, SchemaBaseSchema


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


class EntityChangeDetailSchema(BaseModel):
    created_at: datetime
    reviewed_at: Optional[datetime]
    created_by: str
    reviewed_by: Optional[str]
    status: ChangeStatus
    entity: ChangedEntitySchema
    comment: Optional[str]
    changes: dict[str, EntityChangeSchema]


class RecentChangeSchema(BaseModel):
    created_at: datetime
    status: ChangeStatus
    id: int

    class Config:
        orm_mode = True


class SchemaChangesSchema(BaseModel):
    name: Optional[Dict[str, str]]
    slug: Optional[Dict[str, str]]
    reviewable: Optional[Dict[str, bool]]
    deleted: Optional[Dict[str, bool]]
    add: Optional[List[AttrDefSchema]]
    update: Optional[List[AttrDefUpdateSchema]]
    delete: Optional[List[str]]


class SchemaChangeDetailSchema(BaseModel):
    created_at: datetime
    reviewed_at: Optional[datetime]
    created_by: str
    reviewed_by: Optional[str]
    status: ChangeStatus
    schema_: SchemaBaseSchema = Field(alias='schema')
    comment: Optional[str]
    changes: SchemaChangesSchema