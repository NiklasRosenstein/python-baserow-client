
import dataclasses
import typing as t


@dataclasses.dataclass
class User:
  first_name: str
  username: str


@dataclasses.dataclass
class Group:
  id: int
  name: str


@dataclasses.dataclass
class OrderedGroup:
  order: int


@dataclasses.dataclass
class Table:
  id: int
  name: str
  order: int
  database_id: int


@dataclasses.dataclass
class TableField:
  id: int
  table_id: int
  name: str
  order: int
  type: str
  primary: bool
  text_default: str


@dataclasses.dataclass
class Application:
  id: int
  name: str
  order: int
  type: str
  group: Group
  tables: t.List[Table]
