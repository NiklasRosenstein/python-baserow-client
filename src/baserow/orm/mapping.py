
import dataclasses
import json
import typing as t
from pathlib import Path

import databind.json

from ..client import BaserowClient
from .model import ModelMappingDescription


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

  def to_json(self) -> t.Dict[str, t.Any]:
    return databind.json.dump(self)

  @staticmethod
  def load(filename: t.Union[str, Path]) -> 'DatabaseMapping':
    return databind.json.loads(Path(filename).read_text(), DatabaseMapping)

  def save(self, filename: t.Union[str, Path], indent: t.Optional[int] = None) -> None:
    Path(filename).write_text(json.dumps(self.to_json(), indent=indent))
