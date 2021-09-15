
import dataclasses
import datetime
import enum
import typing as t

Orderable = t.Union[int, float]
BasicType = t.Union[bool, str, Orderable]
Date = t.Union[datetime.date, datetime.datetime]
ValueType = t.Union[BasicType, Date]


class FilterType(enum.Enum):
  OR = enum.auto()
  AND = enum.auto()


class FilterMode(enum.Enum):
  equal = enum.auto()
  not_equal = enum.auto()
  filename_contains = enum.auto()
  contains = enum.auto()
  contains_not = enum.auto()
  higher_than = enum.auto()
  lower_than = enum.auto()
  date_equal = enum.auto()
  date_before = enum.auto()
  date_after = enum.auto()
  date_not_equal = enum.auto()
  date_equals_today = enum.auto()
  date_equals_month = enum.auto()
  date_equals_year = enum.auto()
  single_select_equal = enum.auto()
  single_select_not_equal = enum.auto()
  link_row_has = enum.auto()
  link_row_has_not = enum.auto()
  boolean = enum.auto()
  empty = enum.auto()
  not_empty = enum.auto()


@dataclasses.dataclass
class Filter:
  field: str
  filter: FilterMode
  value: t.Optional[ValueType]

  def to_query_parameter(self) -> t.Tuple[str, t.Optional[str]]:
    key = f'filter__{self.field}__{self.filter.name}'
    value: t.Optional[str]
    if isinstance(self.value, datetime.datetime):
      value = self.value.strftime('%Y-%m-%dT%H:%M:%S%z')
    elif isinstance(self.value, datetime.date):
      value = self.value.strftime('%Y-%m-%d')
    elif self.value is None:
      value = None
    else:
      value = str(self.value)
    return (key, value)


class Column:
  """
  A helper class to build #Filter#s.
  """

  def __init__(self, name: str) -> None:
    self._name = name

  def equal(self, value: ValueType) -> Filter:
    return Filter(self._name, FilterMode.equal, value)

  def not_equal(self, value: ValueType) -> Filter:
    return Filter(self._name, FilterMode.not_equal, value)

  def filename_contains(self, value: str) -> Filter:
    return Filter(self._name, FilterMode.filename_contains, value)

  def contains(self, value: str) -> Filter:
    return Filter(self._name, FilterMode.contains, value)

  def contains_not(self, value: str) -> Filter:
    return Filter(self._name, FilterMode.contains_not, value)

  def higher_than(self, value: Orderable) -> Filter:
    return Filter(self._name, FilterMode.higher_than, value)

  def lower_than(self, value: Orderable) -> Filter:
    return Filter(self._name, FilterMode.lower_than, value)

  def date_equal(self, value: Date) -> Filter:
    return Filter(self._name, FilterMode.date_equal, value)

  def date_before(self, value: Date) -> Filter:
    return Filter(self._name, FilterMode.date_before, value)

  def date_after(self, value: Date) -> Filter:
    return Filter(self._name, FilterMode.date_after, value)

  def date_not_equal(self, value: Date) -> Filter:
    return Filter(self._name, FilterMode.date_not_equal, value)

  def date_equals_today(self) -> Filter:
    return Filter(self._name, FilterMode.date_equals_today, None)

  def date_equals_month(self, month: int) -> Filter:
    return Filter(self._name, FilterMode.date_equals_month, month)

  def date_equals_year(self, year: int) -> Filter:
    return Filter(self._name, FilterMode.date_equals_year, year)

  def single_select_equal(self, value: str) -> Filter:
    return Filter(self._name, FilterMode.single_select_equal, value)

  def single_select_not_equal(self, value: str) -> Filter:
    return Filter(self._name, FilterMode.single_select_not_equal, value)

  def link_row_has(self, value: int) -> Filter:
    return Filter(self._name, FilterMode.link_row_has, value)

  def link_row_has_not(self, value: int) -> Filter:
    return Filter(self._name, FilterMode.link_row_has_not, value)

  # def boolean(self, value: ValueType) -> Filter:
  #   return Filter(self._name, FilterMode.boolean, value)

  def empty(self) -> Filter:
    return Filter(self._name, FilterMode.empty, None)

  def not_empty(self) -> Filter:
    return Filter(self._name, FilterMode.not_empty, None)
