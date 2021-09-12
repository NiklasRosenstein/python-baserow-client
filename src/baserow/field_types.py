
import dataclasses
import enum
import typing as t

from databind.core.annotations import union

from .types import TableField


class NumberType(enum.Enum):
  INTEGER = enum.auto()
  DECIMAL = enum.auto()


@dataclasses.dataclass
class SelectOption:
  id: int
  value: str
  color: str


@union.subtype(TableField, 'text')
@dataclasses.dataclass
class TextTableField(TableField):
  text_default: str


@union.subtype(TableField, 'long_text')
@dataclasses.dataclass
class LongTextTableField(TableField): pass


@union.subtype(TableField, 'number')
@dataclasses.dataclass
class NumberTableField(TableField):
  number_decimal_places: int
  number_negative: bool
  number_type: NumberType


@union.subtype(TableField, 'single_select')
@dataclasses.dataclass
class SingleSelectTableField(TableField):
  select_options: t.List[SelectOption]


@union.subtype(TableField, 'url')
@dataclasses.dataclass
class UrlTableField(TableField):
  pass


@union.subtype(TableField, 'link_row')
@dataclasses.dataclass
class LinkRowTableField(TableField):
  link_row_table: int
  link_row_related_field: int


@union.subtype(TableField, 'boolean')
@dataclasses.dataclass
class BooleanTableField(TableField): pass


@union.subtype(TableField, 'file')
@dataclasses.dataclass
class FileTableField(TableField): pass
