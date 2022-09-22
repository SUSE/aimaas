from enum import Enum, auto
from typing import NamedTuple


class Filter(NamedTuple):
    name: str
    op: str
    description: str


class FilterEnum(Enum):
    EQ = Filter('eq', '__eq__', 'equal to')
    LT = Filter('lt', '__lt__', 'less than')
    GT = Filter('gt', '__gt__', 'greater than')
    LE = Filter('le', '__le__', 'less than of equal to')
    GE = Filter('ge', '__ge__', 'greater than or equal to')
    NE = Filter('ne', '__ne__', 'not equal to')
    CONTAINS = Filter('contains', 'icontains', 'contains substring')
    REGEXP = Filter('regexp', 'iregexp_match', 'matches regular expression')
    STARTS = Filter('starts', 'istartswith', 'starts with substring')
    IEQ = Filter('ieq', 'ieq', 'equal to (case insensitive)')


class ModelVariant(Enum):
    CREATE = auto()
    GET = auto()
    LIST = auto()
    UPDATE = auto()
