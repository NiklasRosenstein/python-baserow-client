
import typing as t
import uuid

from ..filter import Column as _Column

if t.TYPE_CHECKING:
  from .model import Model


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


class ForeignKey(Column):

  def __init__(self, user_name: str, model: t.Union[t.Type['Model'], t.Callable[[], t.Type['Model']]]) -> None:
    super().__init__(user_name)
    self._model = model

  @property
  def model(self) -> t.Type['Model']:
    if isinstance(self._model, type):
      return self._model
    self._model = self._model()
    return self._model
