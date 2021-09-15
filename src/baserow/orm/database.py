
import copy
import typing as t

from ..client import BaserowClient
from ..filter import Filter, ValueType
from ..types import Page
from .column import ForeignKey
from .exc import NoRowReturned
from .mapping import DatabaseMapping
from .model import Model

T_Model = t.TypeVar('T_Model', bound='Model')


class ColumnPlaceholderTranslator(t.Dict[str, int]):
  """
  A helper class that translates #Column.id placeholders to Baserow internal field IDs.
  """

  def __init__(self, mapping: DatabaseMapping) -> None:
    self._mapping = mapping
    self._visited: t.Set[t.Type[Model]] = set()

  def visit(self, model: t.Type[Model]) -> None:
    """
    Make the runtime definition of *model* known to the converter. This is needed to ensure that we know the
    column placeholder IDs and how they are mapped to Baserow internal field IDs.
    """

    if model not in self._visited:
      for key, column in model.__columns__.items():
        self[column.id] = self._mapping.models[model.__id__].fields[key]
      self._visited.add(model)


class Database:
  """
  ORM for a Baserow database.
  """

  def __init__(self, client: BaserowClient, mapping: DatabaseMapping) -> None:
    """
    # Arguments
    client: The Baserow client to interact with.
    mapping: A previously generated mapping for the database, it's tables and internal field IDs.
    """

    self._client = client
    self._mapping = mapping
    self._translator = ColumnPlaceholderTranslator(mapping)

  def __repr__(self) -> str:
    return f'Database(db={self._mapping.database_id})'

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
      record[attr_name] = column.from_baserow(self, value)
    return model(record_id, **record)

  def _preprocess_filter(self, filter: Filter) -> Filter:
    """
    Internal. Called by the #Query to replace column placeholders with Baserow internal field IDs.
    """

    if filter.field in self._translator:
      filter = copy.copy(filter)
      filter.field = f'field_{self._translator[filter.field]}'

    return filter

  def select(self, model: t.Type[T_Model]) -> 'Query[T_Model]':
    """
    Create a new #Query for rows of the given model.
    """

    self._translator.visit(model)
    return Query(self, model)

  def save(self, row: Model) -> None:
    """
    Save a model instance as a raw in its backing database. if the *row* has an ID, the method will perform an
    upadte of the row in Baserow. The #Model.id will be set after creation of a new row.
    """

    mapping = self._mapping.models[row.__id__]
    record: t.Dict[str, t.Any] = {}
    for key, col in row.__columns__.items():
      record[f'field_{mapping.fields[key]}'] = col.to_baserow(getattr(row, key))

    if row.id is None:
      row.id = self._client.create_database_table_row(mapping.table_id, record)['id']
    else:
      self._client.update_database_table_row(mapping.table_id, row.id, record)


class Query(t.Generic[T_Model]):
  """
  Represents a query for the rows of a particular model. A query can be modified until it is executed,
  after which it becomes immutable. Iterating over a query yields all matching rows as model instances.
  """

  def __init__(self, db: Database, model: t.Type[T_Model]) -> None:
    self._db = db
    self._model = model
    self._mapping = db._mapping.models[model.__id__]
    self._filters: t.List[Filter] = []
    self._page_size: t.Optional[int] = None
    self._paginator: t.Optional[t.Iterator[Page[t.Dict[str, str]]]] = None
    self._page_items: t.Optional[t.Iterator[t.Dict[str, str]]] = None

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

  @property
  def executed(self) -> bool:
    """
    Returns #True if the query has been executed.
    """

    return self._paginator is not None

  def filter(self, *filters: Filter) -> 'Query[T_Model]':
    """
    Filter the query with the specified filters. This method modified the query.
    """

    if self.executed:
      raise RuntimeError('Query has already been executed')
    for filter in filters:
      self._filters.append(self._db._preprocess_filter(filter))
    return self

  def page_size(self, page_size: int) -> 'Query[T_Model]':
    """
    Set the number of rows to return per call to the Baserow API. This method modified the query.
    """

    if self.executed:
      raise RuntimeError('Query has already been executed')
    self._page_size = page_size
    return self

  def first(self) -> T_Model:
    """
    Return the first row from the query. This method executes the query.

    If the query returns no rows, a #NoRowReturned exception will be raised instead.
    """

    if self.executed:
      raise RuntimeError('Query has already been executed')

    self.page_size(1)
    try:
      return next(self)
    except StopIteration:
      raise NoRowReturned
