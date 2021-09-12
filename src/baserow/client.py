
import dataclasses
import typing as t

import databind.json
import requests

from .filter import Filter, FilterType
from .types import Application, Page, PermissionedOrderedGroup, Table, TableField, User


@dataclasses.dataclass
class ApiError(Exception):
  error: str
  detail: str

  def __str__(self) -> None:
    return f'{self.error}: {self.detail}'


class BaseClient:

  def __init__(self, url: str, token: str) -> None:
    self._url = url.rstrip('/')
    self._session = requests.Session()
    self._session.headers['Authorization'] = f'JWT {token}'

  def _request(self, method: str, path: str, **kwargs) -> requests.Response:
    response = self._session.request(method, self._url + '/' + path.lstrip('/'), **kwargs)
    if (response.status_code // 100) in (4, 5) and response.headers.get('Content-Type') == 'application/json':
      data = response.json()
      raise ApiError(data['error'], data['detail'])
    response.raise_for_status()
    return response


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
    response = self._request('GET', f'/api/database/tables/{table_id}').json()
    return databind.json.load(response, Table)

  def update_database_table(self, table_id: int, name: str) -> Table:
    response = self._request('PATCH', f'/api/database/tables/{table_id}', json={'name': name}).json()
    return databind.json.load(response, Table)

  def list_database_tables(self, database_id: int) -> t.List[Table]:
    response = self._request('GET', f'/api/database/tables/database/{database_id}').json()
    return databind.json.load(response, t.List[Table])

  def list_database_table_fields(self, table_id: int) -> t.List[TableField]:
    response = self._request('GET', f'/api/database/fields/table/{table_id}').json()
    return databind.json.load(response, t.List[TableField])

  def list_database_table_rows(
    self,
    table_id: int,
    exclude: t.Optional[t.List[str]] = None,
    filter: t.List[t.List[Filter]] = None,
    filter_type: t.Optional[FilterType] = None,
    include: t.Optional[t.List[str]] = None,
    order_by: t.Optional[t.List[str]] = None,
    page: t.Optional[int] = None,
    search: t.Optional[str] = None,
    size: t.Optional[int] = None,
    user_field_names: bool = False,
  ) -> Page[t.Dict[str, t.Any]]:

    params = {}
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
      params['page'] = page
    if search is not None:
      params['search'] = search
    if size is not None:
      params['size'] = size
    if user_field_names:
      params['user_field_names'] = True

    response = self._request('GET', f'/api/database/rows/table/{table_id}/', params=params).json()
    if page is None:
      page = 1

    return Page(
      response['count'],
      page - 1 if page > 1 else None,
      page + 1 if response['next'] else None,
      response['results'])

  def paginated_database_table_rows(
    self,
    table_id: int,
    exclude: t.Optional[t.List[str]] = None,
    filter: t.List[t.List[Filter]] = None,
    filter_type: t.Optional[FilterType] = None,
    include: t.Optional[t.List[str]] = None,
    order_by: t.Optional[t.List[str]] = None,
    page: t.Optional[int] = None,
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
