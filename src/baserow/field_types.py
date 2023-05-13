
import dataclasses
import enum
import typing as t

from databind.core.settings import Union

from .types import TableField


class NumberType(enum.Enum):
  INTEGER = enum.auto()
  DECIMAL = enum.auto()


@dataclasses.dataclass
class SelectOption:
  id: int
  value: str
  color: str


@Union.register(TableField, 'text')
@dataclasses.dataclass
class TextTableField(TableField):
  text_default: str


@Union.register(TableField, 'long_text')
@dataclasses.dataclass
class LongTextTableField(TableField): pass


@Union.register(TableField, 'number')
@dataclasses.dataclass
class NumberTableField(TableField):
  number_decimal_places: int
  number_negative: bool
  number_type: NumberType


@Union.register(TableField, 'single_select')
@dataclasses.dataclass
class SingleSelectTableField(TableField):
  select_options: t.List[SelectOption]


@Union.register(TableField, 'url')
@dataclasses.dataclass
class UrlTableField(TableField):
  pass


@Union.register(TableField, 'link_row')
@dataclasses.dataclass
class LinkRowTableField(TableField):
  link_row_table: int
  link_row_related_field: int


@Union.register(TableField, 'boolean')
@dataclasses.dataclass
class BooleanTableField(TableField): pass


@Union.register(TableField, 'file')
@dataclasses.dataclass
class FileTableField(TableField): pass
