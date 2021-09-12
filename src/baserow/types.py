
import dataclasses
import enum
import typing as t

from databind.core.annotations import union

T = t.TypeVar('T')


class Permissions(enum.Enum):
  MEMBER = enum.auto()
  ADMIN = enum.auto()


@dataclasses.dataclass
class User:
  id: int
  first_name: str
  username: str
  is_staff: bool


@dataclasses.dataclass
class Group:
  id: int
  name: str


@dataclasses.dataclass
class OrderedGroup(Group):
  order: int


@dataclasses.dataclass
class PermissionedOrderedGroup(OrderedGroup):
  permissions: Permissions


@dataclasses.dataclass
class Table:
  id: int
  name: str
  order: int
  database_id: int


@union(style=union.Style.flat, constructible=True)
@dataclasses.dataclass
class TableField:
  id: int
  table_id: int
  name: str
  order: int
  primary: bool


@dataclasses.dataclass
class Application:
  id: int
  name: str
  order: int
  type: str
  group: Group
  tables: t.List[Table]


@dataclasses.dataclass
class Page(t.Generic[T]):
  count: int
  previous: t.Optional[int]
  next: t.Optional[int]
  results: t.List[T]


from . import field_types
