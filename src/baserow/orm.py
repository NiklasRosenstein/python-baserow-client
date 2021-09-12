
import copy
import dataclasses
import json
import typing as t
import uuid
from pathlib import Path

import databind.json

from .client import BaserowClient
from .filter import Column as _Column, Filter
from .types import Page

T_Model = t.TypeVar('T_Model', bound='Model')


@dataclasses.dataclass
class ModelMappingPair:
  model_id: str
  table_name: str


class Column(_Column):

  def __init__(self, user_name: str) -> None:
    assert isinstance(user_name, str)
    # We later replace references to this ID in #Filter objects with the actual internal field ID.
    super().__init__(user_name + '.' + str(uuid.uuid4()))
    self._user_name = user_name

  def __repr__(self) -> str:
    return f'{type(self).__name__}(name={self.name!r})'

  @property
  def id(self) -> str:
    return self._name

  @property
  def name(self) -> str:
    return self._user_name


class Model:
  """
  Base class to represent a Baserow table. Static class members on the base class that are instances of the
  #Column class are recognized as fields that are associated with fields in a Baserow database table.
  """

  id: t.Optional[int]
  __id__: t.ClassVar[str]
  __columns__: t.ClassVar[t.Dict[str, Column]]

  def __init_subclass__(cls) -> None:
    if not hasattr(cls, '__id__'):
      cls.__id__ = cls.__module__ + '.' + cls.__name__

    for key, value in vars(cls).items():
      if isinstance(value, Column):
        cls.__columns__[key] = value

    # Inherit parent class columns.
    for base in cls.__bases__:
      if issubclass(base, Model):
        for key, value in base.__columns__.items():
          if key not in cls.__columns__:
            cls.__columns__[key] = copy.copy(value)

    if 'id' in cls.__columns__:
      raise ValueError(f'attribute name "id" is reserved')

  def __init__(self, id: t.Optional[int], **kwargs) -> None:
    self.id = id
    for key, col in self.__columns__.items():
      if key not in kwargs:
        raise TypeError(f'{type(self).__name__}(): missing keyword argument {key!r}')
      setattr(self, key, kwargs[key])
    for key in kwargs:
      if key not in self.__columns__:
        raise TypeError(f'{type(self).__name__}(): unrecognized keyword argument {key!r}')

  def __repr__(self) -> str:
    primary = next(iter(self.__columns__))
    return f'{type(self).__name__}(id={self.id}, {primary}={getattr(self, primary)!r})'

  def as_dict(self) -> t.Dict[str, t.Any]:
    return {'id': self.id, **{k: getattr(self, k) for k in self.__columns__}}

  @classmethod
  def of(cls, table_name: str, field_name_overrides: t.Optional[t.Dict[str, str]] = None) -> 'ModelMappingDescription':
    return ModelMappingDescription(cls.__id__, cls.__columns__, table_name, field_name_overrides or {})


Model.__columns__ = {}


@dataclasses.dataclass
class ModelMappingDescription:
  model_id: str
  columns: t.Dict[str, Column]
  table_name: str
  field_name_overrides: t.Dict[str, str]


@dataclasses.dataclass
class ModelMapping:
  #: The table ID in Baserow.
  table_id: int

  #: Maps field names defined in the Model to internal field IDs.
  fields: t.Dict[str, int]

  def __post_init__(self) -> None:
    self._reverse_fields: t.Optional[t.Dict[int, str]] = {}

  @property
  def reverse_fields(self) -> t.Dict[int, str]:
    if self._reverse_fields is None or len(self.fields) != len(self._reverse_fields):
      self._reverse_fields = {v: k for k, v in self.fields.items()}
    return self._reverse_fields


@dataclasses.dataclass
class DatabaseMapping:
  #: The database ID in Baserow.
  database_id: int

  #: The models included in this database mapping.
  models: t.Dict[str, ModelMapping]

  @staticmethod
  def generate(client: BaserowClient, dbname: str, *models: ModelMappingDescription) -> 'DatabaseMapping':
    """
    Generate a mapping for the database and the given *models* which contains the actual database,
    table and field IDs from Baserow.

    # Example

    ```py
    if client.jwt:
      mapping = DatabaseMapping.generate(client, 'Blog', Post.of('Posts'))
      mapping.save('mapping.json')
    else:
      mapping = DatabaseMapping.load('mapping.json')

    db = Database(client, mapping)
    ```
    """

    try:
      db = next(db for db in client.list_all_applications() if db.name == dbname)
    except StopIteration:
      raise ValueError(f'database {dbname!r} does not exist')

    model_mappings: t.Dict[str, ModelMapping] = {}

    for model in models:
      try:
        table = next(t for t in db.tables if t.name == model.table_name)
      except StopIteration:
        raise ValueError(f'table {dbname!r}/{model.table_name!r} does not exist')

      table_fields = {f.name: f for f in client.list_database_table_fields(table.id)}
      fields: t.Dict[str, str] = {}
      for key, column in model.columns.items():
        name = model.field_name_overrides.get(key) or column.name
        if name not in table_fields:
          raise ValueError(f'field {dbname!r}/{model.table_name!r}/{name} does not exist')
        fields[key] = table_fields[name].id

      model_mappings[model.model_id] = ModelMapping(table.id, fields)

    return DatabaseMapping(db.id, model_mappings)

  @staticmethod
  def load(filename: t.Union[str, Path]) -> 'DatabaseMapping':
    return databind.json.loads(Path(filename).read_text(), DatabaseMapping)

  def save(self, filename: t.Union[str, Path], indent: t.Optional[int] = None) -> None:
    Path(filename).write_text(json.dumps(databind.json.dump(self), indent=indent))


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

    row.pop('order', None)
    record_id = row.pop('id')
    record = {}
    for key, value in row.items():
      assert key.startswith('field_')
      field_id = int(key[6:])
      if field_id in self._mapping.reverse_fields:
        record[self._mapping.reverse_fields[field_id]] = value

    return self._model(record_id, **record)

  def _begin(self) -> None:
    self._paginator = self._db._client.paginated_database_table_rows(
      self._mapping.table_id,
      filter=self._filters)

  def filter(self, *filters: Filter) -> 'Query[T_Model]':
    for filter in filters:
      self._filters.append(self._db._preprocess_filter(filter))
    return self
