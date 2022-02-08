from enum import Enum
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
    CONTAINS = Filter('contains', 'contains', 'constains substring')
    REGEXP = Filter('regexp', 'regexp_match', 'matches regular expression')
    STARTS = Filter('starts', 'startswith', 'starts with substring')


