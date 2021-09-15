
import typing as t
import uuid

from ..filter import Column as _Column, ValueType

if t.TYPE_CHECKING:
  from .database import Database
  from .model import Model

T_Model = t.TypeVar('T_Model', bound='Model')


class Column(_Column):
  """
  Use this class to declare a column on the class-level of a #Model subclass. Colums declared with this
  class will be assigned to a #Model instance directly (unlike, for example, the #ForeignKey column type).

  # Example

  ```py
  from baserow.orm import Column, Model

  class Product(Model):
    name = Column('Name')
    price = Column('Price')
  ```

  Columns have four types of names:

  1. The attrribute name that is assigned to them on the Model instance and that is used to reference the
     column in code.
  2. The user defined name of the column (aka. field) in the Baserow table.
  3. The Baserow internal field ID.
  4. An ORM internal UUID that is newly generated every for every Column instance. This ID is used as a
     placeholder when constructing #Filter#s which the #Query will replace with the Baserow internal
     field ID on execution.

  In the model, we only specify the attribute and user defined name. Use the #DatabaseMapping.generate()
  method, or the `baserow.orm` CLI, to generate a #DatabaseMapping which uses the user defined name to
  create a mapping from attribute name to Baserow internal field ID.
  """

  def __init__(self, user_name: str) -> None:
    """
    # Arguments
    user_name: The user specified column name in the Baserow table.
    """

    assert isinstance(user_name, str)
    # We later replace references to this ID in #Filter objects with the actual internal field ID.
    super().__init__(user_name + '.' + str(uuid.uuid4()))
    self._user_name = user_name

  def __repr__(self) -> str:
    return f'{type(self).__name__}(name={self.name!r})'

  def from_baserow(self, db: 'Database', value: t.Any) -> t.Any:
    """
    Convert a value received by Baserow for this column to the value that should be assigned to the
    Model instance attribute.
    """

    return value

  def to_baserow(self, value: t.Any) -> t.Any:
    """
    Convert a value stored on a model instance to JSON format for a request to Baserow.
    """

    return value

  def from_python(self, value: t.Any) -> t.Any:
    """
    Convert a value assigned to the row from Python.
    """

    return value

  @property
  def id(self) -> str:
    """
    The internal ID of the column that is used a as a placeholder when constructing #Filter#s.
    """

    return self._name

  @property
  def name(self) -> str:
    """
    The user defined name of the column.
    """

    return self._user_name


class ForeignKey(Column):
  """
  The #ForeignKey is a special column that should be used to represent a "link row" field in Baserow. Model
  attributes of this column type will not receive the raw data from the Baserow API as values, but instead
  an instance of #LinkedRow which automatically loads the linked rows as another Model from the database on
  access.
  """

  def __init__(self, user_name: str, model: t.Union[t.Type['Model'], t.Callable[[], t.Type['Model']]]) -> None:
    super().__init__(user_name)
    self._model = model

  def from_baserow(self, db: 'Database', value: t.Any) -> t.Any:
    refs = [Ref(x['id'], x['value']) for x in value]
    return LinkedRow(db, self.model, refs)

  def to_baserow(self, value: t.Any) -> t.Any:
    assert isinstance(value, LinkedRow)
    return [r.id for r in value.refs]

  def from_python(self, value: t.Any) -> t.Any:
    if not isinstance(value, t.Collection):
      raise TypeError(f'expected collection for column {self.name}')
    value_list = list(value)
    for item in value_list:
      if not isinstance(item, self.model):
        raise TypeError(f'expeted {self.model.__id__!r} instance for column {self.name}')
    # TODO (@NiklasRosenstein): Need to know which is the primary column in the model
    raise NotImplementedError
    # primary_col = ...
    # refs = [Ref(x.id, getattr(x, primary_col)) for x in value]
    # return LinkedRow(None, self._model, refs, {x.id: x for x in value_list})

  @property
  def model(self) -> t.Type['Model']:
    if isinstance(self._model, type):
      return self._model
    self._model = self._model()
    return self._model


class Ref(t.NamedTuple):
  """
  A reference to another row.
  """

  id: int
  name: ValueType


class LinkedRow(t.Sequence[T_Model]):
  """
  Represents a "link row" field. Loads instances of the linked Model on acces.
  """

  def __init__(
    self,
    db: t.Optional['Database'],
    model: t.Type[T_Model],
    values: t.List[Ref],
    cache: t.Optional[t.Dict[int, T_Model]] = None,
  ) -> None:
    self._db = db
    self._model = model
    self._refs = values
    self._cache: t.Dict[int, T_Model] = cache or {}

  def __repr__(self) -> str:
    return f'{type(self).__name__}({self._refs!r})'

  def __len__(self) -> int:
    return len(self._refs)

  def __iter__(self) -> t.Iterator[T_Model]:
    for i in range(len(self._refs)):
      yield self[i]

  def __getitem__(self, index: int) -> T_Model:  # type: ignore
    if index in self._cache:
      return self._cache[index]
    assert self._db is not None, 'not attached to a database'
    self._cache[index] = result = self._db._load_single(self._model, self._refs[index].id)
    return result

  @property
  def refs(self) -> t.List[Ref]:
    return self._refs
