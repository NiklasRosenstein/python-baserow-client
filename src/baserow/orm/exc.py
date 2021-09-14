

class BaserowOrmException(Exception):
  pass


class NoRowReturned(BaserowOrmException):
  """
  This exception is raised by the #Query class if at least one row was expected but none was returned
  by the Baserow API.
  """
