import enum


class EditableObjectType(enum.Enum):
    SCHEMA = 'SCHEMA'
    ENTITY = 'ENTITY'


class ContentType(enum.Enum):
    ATTRIBUTE = 'ATTRIBUTE'
    ATTRIBUTE_DEFINITION = 'ATTRIBUTE_DEFINITION'
    ENTITY = 'ENTITY'
    SCHEMA = 'SCHEMA'


class ReviewResult(enum.Enum):
    APPROVE = 'APPROVE'
    DECLINE = 'DECLINE'


class ChangeStatus(enum.Enum):
    PENDING = 'PENDING'
    DECLINED = 'DECLINED'
    APPROVED = 'APPROVED'


class ChangeType(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    RESTORE = 'RESTORE'
