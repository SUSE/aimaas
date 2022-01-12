from enum import Enum


class PermissionTargetType(Enum):
    SCHEMA = "Schema"
    ENTITY = "Entity"
    GROUP = "Group"


class PermissionType(Enum):
    SUPERUSER = "SU"
    USER_MANAGEMENT = "UM"
    CREATE_SCHEMA = "SCH_C"
    UPDATE_SCHEMA = "SCH_U"
    DELETE_SCHEMA = "SCH_D"
    READ_SCHEMA = "SCH_R"
    CREATE_ENTITY = "ENT_C"
    UPDATE_ENTITY = "ENT_U"
    DELETE_ENTITY = "ENT_D"
    READ_ENTITY = "ENT_R"


class RecipientType(Enum):
    USER = "User"
    GROUP = "Group"
