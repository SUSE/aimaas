from typing import Any, List, Optional, Union

from .models import Entity


class SchemaExistsException(Exception):
    def __init__(self, name: str, slug: str):
        self.name = name
        self.slug = slug

    def __str__(self) -> str:
        return f'Schema with name `{self.name}` or slug `{self.slug}` already exists'

class EntityExistsException(Exception):
    def __init__(self, slug: str):
        self.slug = slug

    def __str__(self) -> str:
        return f'Entity with slug `{self.slug}` already exists in this schema'


class GroupExistsException(Exception):
    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return f'Group with name {self.name} already exists'


class MissingObjectException(Exception):
    obj_type: str = "Object"

    def __init__(self, obj_id: Union[int, str], obj_type: Optional[str] = None):
        self.obj_id = obj_id
        self.obj_type = obj_type or self.obj_type

    def __str__(self) -> str:
        return f"{self.obj_type} with id {self.obj_id} doesn't exist or was deleted"

class MissingSchemaException(MissingObjectException):
    obj_type = 'Schema'

class MissingEntityException(MissingObjectException):
    obj_type = 'Entity'

class MissingAttributeException(MissingObjectException):
    obj_type = 'Attribute'


class MissingChangeException(MissingObjectException):
    obj_type = 'Change'


class MissingChangeRequestException(MissingObjectException):
    obj_type = "ChangeRequest"


class MissingEntityUpdateRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no entity update request with id {self.obj_id}'


class MissingEntityDeleteRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no entity delete request with id {self.obj_id}'


class MissingEntityCreateRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no entity create request with id {self.obj_id}'


class MissingSchemaCreateRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no schema create request with id {self.obj_id}'


class MissingSchemaUpdateRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no schema update request with id {self.obj_id}'


class MissingSchemaDeleteRequestException(MissingObjectException):
    def __str__(self) -> str:
        return f'There is no schema delete request with id {self.obj_id}'


class MissingUserException(MissingObjectException):
    obj_type = 'User'


class MissingPermissionException(MissingObjectException):
    obj_type = 'Permission'


class MissingGroupPermissionException(MissingObjectException):
    obj_type = 'Group permission'


class MissingGroupException(MissingObjectException):
    obj_type = 'Group'


class MissingUserGroupException(MissingObjectException):
    def __init__(self, user_id, group_id):
        self.user_id = user_id
        self.group_id = group_id

    def __str__(self):
        return f"User {self.user_id} is not a member of group {self.group_id}"


class MultipleAttributeOccurencesException(Exception):
    def __init__(self, attr_name: str):
        self.attr_name = attr_name
    
    def __str__(self) -> str:
        return f'Found multiple occurrences of attribute `{self.attr_name}`'

class NoSchemaToBindException(Exception):
    def __init__(self, attr_id: int):
        self.attr_id = attr_id

    def __str__(self) -> str:
        return f'You must bind attribute with id {self.attr_id} to some schema'

class WrongSchemaToBindException(Exception):
    def __init__(self, attr_name: str, schema_id: int, bound_schema_id: int, passed_entity: Entity):
        self.attr_name = attr_name
        self.schema_id = schema_id
        self.bound_schema_id = bound_schema_id
        self.passed_entity = passed_entity

    def __str__(self) -> str:
        return f'Attribute `{self.attr_name}` defined on schema ({self.schema_id}) is bound to schema ({self.bound_schema_id}); got instead entity ({self.passed_entity.id}) from schema ({self.passed_entity.schema_id})'


class BaseAttributeException(Exception):
    def __init__(self, attr_id: int, schema_id: int):
        self.attr_id = attr_id
        self.schema_id = schema_id

class AttributeAlreadyDefinedException(BaseAttributeException):
    def __str__(self) -> str:
        return f'Attribute ({self.attr_id}) is already defined on schema ({self.schema_id}).'

class AttributeNotDefinedException(BaseAttributeException):
    def __str__(self) -> str:
        return f'Attribute ({self.attr_id}) is not defined on schema ({self.schema_id}).'


class InvalidAttributeChange(BaseAttributeException):
    def __init__(self, attr_id: int, schema_id: int, field: str):
        super().__init__(attr_id=attr_id, schema_id=schema_id)
        self.field = field

    def __str__(self) -> str:
        return f"Changing the field '{self.field}' of attribute ({self.attr_id}) on schema " \
               f"({self.schema_id}) is not allowed."


class ListedToUnlistedException(Exception):
    def __init__(self, attr_def_id: int):
        self.attr_def_id = attr_def_id

    def __str__(self) -> str:
        return f"Attribute definition with id {self.attr_def_id} is listed, can't make unlisted"

class NotListedAttributeException(Exception):
    def __init__(self, attr_name: str, schema_id: int):
        self.attr_name = attr_name
        self.schema_id = schema_id

    def __str__(self) -> str:
        return f"Attribute `{self.attr_name}` on schema ({self.schema_id}) can't hold multiple values"

class UniqueValueException(Exception):
    def __init__(self, attr_name: str, schema_id: int, value: Any):
        self.attr_name = attr_name
        self.schema_id = schema_id
        self.value = value

    def __str__(self) -> str:
        return f'Got non-unique value for field `{self.attr_name}` on schema ({self.schema_id}): {self.value}'


class RequiredFieldException(Exception):
    def __init__(self, field: str):
        self.field = field

    def __str__(self) -> str:
        return f'Missing required field: {self.field}'


class MismatchingSchemaException(Exception):
    def __init__(self, entity_id: int, schema_id: int):
        self.entity_id = entity_id
        self.schema_id = schema_id

    def __str__(self) -> str:
        return f"Requested Entity ({self.entity_id}) doesn't belong to specified Schema ({self.schema_id})"


class ReservedAttributeException(Exception):
    def __init__(self, attr_name: str, reserved: List[str]):
        self.attr_name = attr_name
        self.reserved = reserved

    def __str__(self) -> str:
        return f"Can't create attribute `{self.attr_name}`. List of reserved attribute names: {', '.join(self.reserved)}"


class InvalidFilterOperatorException(Exception):
    def __init__(self, attr: str, filter: str):
        self.attr = attr
        self.filter = filter

    def __str__(self) -> str:
        return f'`{self.filter}` is invalid filter for attribute {self.attr}'


class InvalidFilterAttributeException(Exception):
    def __init__(self, attr: str, allowed_attrs: List[str]):
        self.attr = attr
        self.allowed_attrs = allowed_attrs

    def __str__(self) -> str:
        return f"Can't filter current schema by attribute `{self.attr}`. Allowed attributes: {', '.join(self.allowed_attrs)}"


class NoOpChangeException(Exception):
    pass


class CircularGroupReferenceException(Exception):
    def __str__(self) -> str:
        return 'Made an attempt to inherit from group which either directly or indirectly inherits from current group'
