
import copy
import dataclasses
import typing as t

from .column import Column


class Model:
  """
  Base class to represent a Baserow table. Static class members on the base class that are instances of the
  #Column class are recognized as fields that are associated with fields in a Baserow database table.
  """

  id: t.Optional[int]
  __id__: t.ClassVar[str]
  __tablename__: t.ClassVar[t.Optional[str]]
  __columns__: t.ClassVar[t.Dict[str, Column]]

  def __init_subclass__(cls) -> None:
    cls.__columns__ = {}
    if '__tablename__' not in vars(cls):
      cls.__tablename__ = None

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

  def __init__(self, id: t.Optional[int] = None, **kwargs) -> None:
    self.id = id
    for key, col in self.__columns__.items():
      if key not in kwargs:
        raise TypeError(f'{type(self).__name__}(): missing keyword argument {key!r}')
      setattr(self, key, col.from_python(kwargs[key]))
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
