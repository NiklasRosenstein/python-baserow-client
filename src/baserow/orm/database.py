
import typing as t

from ..client import BaserowClient
from ..filter import Filter, ValueType
from ..types import Page
from .column import ForeignKey
from .exc import NoRowReturned
from .mapping import DatabaseMapping
from .model import Model

T_Model = t.TypeVar('T_Model', bound='Model')


class Database:
  """
  Represents a Baserow database.
  """

  def __init__(self, client: BaserowClient, mapping: DatabaseMapping) -> None:
    """
    # Arguments
    client: The Baserow client to interact with.
    db: The ID of the database.
    """

    self._client = client
    self._mapping = mapping

    self._internal_column_configured: t.Set[str] = set()
    self._internal_column_id_to_field_id: t.Dict[str, int] = {}

  def __repr__(self) -> str:
    return f'Database(db={self._db})'

  def _load_single(self, model: t.Type[T_Model], row_id: int) -> T_Model:
    mapping = self._mapping.models[model.__id__]
    row = self._client.get_database_table_row(mapping.table_id, row_id)
    return self._build_model_from_row(model, row)

  def _build_model_from_row(self, model: t.Type[T_Model], row: t.Dict[str, t.Any]) -> T_Model:
    mapping = self._mapping.models[model.__id__]
    row.pop('order', None)
    record_id = row.pop('id')
    record = {}
    for key, value in row.items():
      assert key.startswith('field_')
      field_id = int(key[6:])
      if field_id not in mapping.reverse_fields:
        continue
      attr_name = mapping.reverse_fields[field_id]
      column = model.__columns__[attr_name]
      if isinstance(column, ForeignKey):
        value = LinkedTableCollection(self, column.model, column, [LinkedTableCollection._RawValue(x['id'], x['value']) for x in value])
      record[attr_name] = value

    return model(record_id, **record)

  def _preprocess_filter(self, filter: Filter) -> Filter:
    if filter.field in self._internal_column_id_to_field_id:
      filter.field = f'field_{self._internal_column_id_to_field_id[filter.field]}'
    return filter

  def select(self, model: t.Type[T_Model]) -> 'Query[T_Model]':
    if model.__id__ not in self._internal_column_configured:
      for key, column in model.__columns__.items():
        self._internal_column_id_to_field_id[column.id] = self._mapping.models[model.__id__].fields[key]
      self._internal_column_configured.add(model.__id__)
    return Query(self, model)


class Query(t.Generic[T_Model]):

  def __init__(self, db: Database, model: t.Type[T_Model]) -> None:
    self._db = db
    self._model = model
    self._mapping = db._mapping.models[model.__id__]
    self._filters: t.List[Filter] = []
    self._page_size = None
    self._paginator: t.Optional[t.Generator[Page[t.Dict[str, str]]]] = None
    self._page_items: t.Optional[t.Iterator[Page[t.Dict[str, str]]]] = None

  def __iter__(self) -> 'Query':
    return self

  def __next__(self) -> T_Model:
    if not self._paginator:
      self._begin()
      assert self._paginator is not None
    while True:
      if self._page_items is None:
        self._page_items = iter(next(self._paginator).results)
      try:
        row = next(self._page_items)
        break
      except StopIteration:
        self._page_items = None
        continue

    return self._db._build_model_from_row(self._model, row)

  def _begin(self) -> None:
    self._paginator = self._db._client.paginated_database_table_rows(
      self._mapping.table_id,
      filter=self._filters)

  def filter(self, *filters: Filter) -> 'Query[T_Model]':
    if self._paginator is not None:
      raise RuntimeError('Query has already been evaluated')
    for filter in filters:
      self._filters.append(self._db._preprocess_filter(filter))
    return self

  def page_size(self, page_size: int) -> 'Query[T_Model]':
    if self._paginator is not None:
      raise RuntimeError('Query has already been evaluated')
    self._page_size = page_size
    return self

  def first(self) -> T_Model:
    """
    Returns the first object from the query, or raises a #NoRowReturned exception.
    """

    if self._paginator is not None:
      raise RuntimeError('Query has already been evaluated')

    self.page_size(1)
    try:
      return next(self)
    except StopIteration:
      raise NoRowReturned


class LinkedTableCollection(t.Sequence[T_Model]):
  """
  This class is used as the value for #LinkColumn#s.
  """

  class _RawValue(t.NamedTuple):
    id: int
    value: ValueType

  def __init__(self, db: Database, model: t.Type[T_Model], column: ForeignKey, values: t.List[_RawValue]) -> None:
    self._db = db
    self._model = model
    self._column = column
    self._values = values
    self._cache: t.Dict[int, T_Model] = {}

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self._values!r})'

  def __len__(self) -> int:
    return len(self._values)

  def __iter__(self) -> t.Iterator[T_Model]:
    for i in range(len(self._values)):
      yield self[i]

  def __getitem__(self, index: int) -> T_Model:
    if index in self._cache:
      return self._cache[index]
    self._cache[index] = result = self._db._load_single(self._model, self._values[index].id)
    return result

  @property
  def raw(self) -> t.List[_RawValue]:
    return self._raw
