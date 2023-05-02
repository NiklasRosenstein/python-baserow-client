
import dataclasses
import json
import logging
import typing as t
from pathlib import Path

import databind.json
import requests

from .filter import Filter, FilterType
from .types import Application, Page, PermissionedOrderedGroup, Table, TableField, User

log = logging.getLogger(__name__)
DEFAULT_CREDENTIALS_FILE = '.baserow-creds.json'


@dataclasses.dataclass
class ApiError(Exception):
  error: str
  detail: str

  def __str__(self) -> str:
    return f'{self.error}: {self.detail}'


class BaseClient:
  """
  Base class for the Baserow client which handles the authentication and request session.

  A JWT is needed when performing requests that are scoped to user interactions (e.g. operations that
  are expected to be run through the UI). A token should be used if only a subset of the Baserow API
  is used to create/read/write/delete rows.
  """

  def __init__(self, url: str, token: t.Optional[str] = None, jwt: t.Optional[str] = None) -> None:
    if token and jwt:
      raise ValueError(f'token/jwt can not be specified at the same time')

    self._url = url.rstrip('/')
    self._session = requests.Session()
    self._jwt: t.Optional[str] = None
    self._token: t.Optional[str] = None

    if jwt:
      self.jwt = jwt
    elif token:
      self.token = token

  def _request(self, method: str, path: str, **kwargs) -> requests.Response:
    response = self._session.request(method, self._url + '/' + path.lstrip('/'), **kwargs)
    if (response.status_code // 100) in (4, 5) and response.headers.get('Content-Type') == 'application/json':
      data = response.json()
      log.debug('Error from %s %s: %s', method, path, data)
      raise ApiError(data.get('error', 'UNKNOWN'), data.get('detail', '???'))
    response.raise_for_status()
    return response

  @property
  def jwt(self) -> t.Optional[str]:
    return self._jwt

  @jwt.setter
  def jwt(self, jwt: str) -> None:
    self._jwt = jwt
    self._token = None
    self._session.headers['Authorization'] = f'JWT {jwt}'

  @property
  def token(self) -> t.Optional[str]:
    return self._token

  @token.setter
  def token(self, token: str) -> None:
    self._jwt = None
    self._token = token
    self._session.headers['Authorization'] = f'Token {token}'


class BaserowClient(BaseClient):
  """
  Client for Baserow servers.
  """

  def get_settings(self) -> t.Dict[str, t.Any]:
    return self._request('GET', '/api/settings/').json()

  def update_settings(self, settings: t.Dict[str, t.Any]) -> None:
    self._request('PATCH', '/api/settings/update/', json=settings)

  def token_auth(self, username: str, password: str) -> t.Tuple[User, str]:
    payload = {'username': username, 'password': password}
    response = self._request('POST', '/api/user/token-auth/', json=payload).json()
    return databind.json.load(response['user'], User), response['token']

  def token_refresh(self, token: str) -> t.Tuple[User, str]:
    payload = {'token': token}
    response = self._request('POST', '/api/user/token-refresh/', json=payload).json()
    return databind.json.load(response['user'], User), response['token']

  def create_user(
    self,
    name: str,
    email: str,
    password: str,
    authenticate: bool = False,
    group_invitation_token: t.Optional[str] = None,
    template_id: t.Optional[int] = None
  ) -> t.Tuple[User, t.Optional[str]]:

    payload: t.Dict[str, t.Union[str, bool, int]] = {'name': name, 'email': email, 'password': password}
    if authenticate:
      payload['authenticate'] = authenticate
    if group_invitation_token:
      payload['group_invitation_token'] = group_invitation_token
    if template_id:
      payload['template_id'] = template_id

    response = self._request('POST', '/api/user/', json=payload).json()
    return databind.json.load(response['user'], User), response.get('token')

  def list_groups(self) -> t.List[PermissionedOrderedGroup]:
    response = self._request('GET', '/api/groups/').json()
    return databind.json.load(response, t.List[PermissionedOrderedGroup])

  def create_group(self, name: str) -> PermissionedOrderedGroup:
    response = self._request('POST', '/api/groups/', json={'name': name}).json()
    return databind.json.load(response, PermissionedOrderedGroup)

  def list_all_applications(self) -> t.List[Application]:
    response = self._request('GET', '/api/applications/').json()
    return databind.json.load(response, t.List[Application])

  def get_database_table(self, table_id: int) -> Table:
    response = self._request('GET', f'/api/database/tables/{table_id}/').json()
    return databind.json.load(response, Table)

  def update_database_table(self, table_id: int, name: str) -> Table:
    response = self._request('PATCH', f'/api/database/tables/{table_id}/', json={'name': name}).json()
    return databind.json.load(response, Table)

  def list_database_tables(self, database_id: int) -> t.List[Table]:
    response = self._request('GET', f'/api/database/tables/database/{database_id}/').json()
    return databind.json.load(response, t.List[Table])

  def list_database_table_fields(self, table_id: int) -> t.List[TableField]:
    response = self._request('GET', f'/api/database/fields/table/{table_id}/').json()
    return databind.json.load(response, t.List[TableField])

  def list_database_table_rows(
    self,
    table_id: int,
    exclude: t.Optional[t.List[str]] = None,
    filter: t.Optional[t.List[Filter]] = None,
    filter_type: t.Optional[FilterType] = None,
    include: t.Optional[t.List[str]] = None,
    order_by: t.Optional[t.List[str]] = None,
    page: t.Optional[int] = None,
    search: t.Optional[str] = None,
    size: t.Optional[int] = None,
    user_field_names: bool = False,
  ) -> Page[t.Dict[str, t.Any]]:

    params: t.Dict[str, t.Optional[str]] = {}
    if exclude is not None:
      params['exclude'] = ','.join(exclude)
    if filter is not None:
      params.update(dict(f.to_query_parameter() for f in filter))
    if filter_type is not None:
      params['filter_type'] = filter_type.name
    if include is not None:
      params['include'] = ','.join(include)
    if order_by is not None:
      params['order_by'] = ','.join(order_by)
    if page is not None:
      params['page'] = str(page)
    if search is not None:
      params['search'] = search
    if size is not None:
      params['size'] = str(size)
    if user_field_names:
      params['user_field_names'] = 'True'

    response = self._request('GET', f'/api/database/rows/table/{table_id}/', params=params).json()
    if page is None:
      page = 1

    return Page(
      response['count'],
      page - 1 if page > 1 else None,
      page + 1 if response['next'] else None,
      response['results'])

  def create_database_table_row(self, table_id: int, record: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    return self._request('POST', f'/api/database/rows/table/{table_id}/', json=record).json()

  def update_database_table_row(self, table_id: int, row_id: int, record: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    return self._request('PATCH', f'/api/database/rows/table/{table_id}/{row_id}/', json=record).json()

  def get_database_table_row(self, table_id: int, row_id: int) -> t.Dict[str, t.Any]:
    return self._request('GET', f'/api/database/rows/table/{table_id}/{row_id}/').json()

  # Extra

  def login(self, username: str, password: str, cache: t.Union[bool, str] = False) -> User:
    """
    A convenience method to log into Baserow using the specified *username* and *password* and updating
    the current client object. If *cache* is enabled or is a filename, it will be used to load a cached
    token for the Baserow URL and username combination to reuse a previously generated JWT. If the reused
    JWT is not valid anymore, the credentials will be used to generate a new one.
    """

    cache_fn = cache if isinstance(cache, str) else None
    if cache:
      user = self.load(username, cache_fn)
      if user:
        return user

    log.info('Creating new JWT')
    user, self.jwt = self.token_auth(username, password)
    if cache:
      self.save(username, cache_fn)
    return user

  def load(self, username: str, filename: t.Optional[str] = None, raise_: bool = False, refresh: bool = True) -> t.Optional[User]:
    """
    Loads an existing JWT from the given *filename* or the #DEFAULT_CREDENTIALS_FILE. Returns #True if a token
    was loaded, #False otherwise. If a token is loaded, it will be immediately refreshed.
    """

    path = Path(filename or DEFAULT_CREDENTIALS_FILE)
    if not path.exists():
      if raise_:
        raise FileNotFoundError(path)
      return None

    try:
      data = json.loads(path.read_text())
    except json.JSONDecodeError:
      log.error('Unable to parse JSON file %s', path)
      if raise_:
        raise
      return None

    jwt = data.get(self._url, {}).get(username)
    if jwt:
      log.info('Refreshing JWT')
      user, self.jwt = self.token_refresh(jwt)
      self.save(username, filename)
      return user

    return None

  def save(self, username: str, filename: t.Optional[str] = None) -> None:
    """
    Saves the JWt of the client into *filename* or the given #DEFAULT_CREDENTIALS_FILE.
    """

    if not self.jwt:
      raise ValueError(f'No JWT set')

    path = Path(filename or DEFAULT_CREDENTIALS_FILE)
    data = json.loads(path.read_text()) if path.exists() else {}
    data.setdefault(self._url, {})[username] = self.jwt
    path.write_text(json.dumps(data, indent=2))

  def paginated_database_table_rows(
    self,
    table_id: int,
    exclude: t.Optional[t.List[str]] = None,
    filter: t.Optional[t.List[Filter]] = None,
    filter_type: t.Optional[FilterType] = None,
    include: t.Optional[t.List[str]] = None,
    order_by: t.Optional[t.List[str]] = None,
    search: t.Optional[str] = None,
    size: t.Optional[int] = None,
    user_field_names: bool = False,
  ) -> t.Generator[Page[t.Dict[str, t.Any]], None, None]:

    page_number = None
    while True:
      page = self.list_database_table_rows(
        table_id=table_id,
        exclude=exclude,
        filter=filter,
        filter_type=filter_type,
        include=include,
        order_by=order_by,
        page=page_number,
        search=search,
        size=size,
        user_field_names=user_field_names,
      )
      if page.results:
        yield page
      if not page.next:
        break
      page_number = page.next
