# Getting started

The Baserow client provides direct access to many of the Baserow API endpoints. It must be initialized with
the URL to your Baserow instance as well as a JWT or Token. Without authentication, the client may still be
used to generate a JWT from user credentials.

__Examples:__

```py
from baserow.client import BaserowClient

client = BaserowClient('https://baserow.io', jwt='...')
client = BaserowClient('https://baserow.io', token='...')

client = BaserowClient('https://baserow.io')
user, jwt = client.token_auth('username', 'password')
```

If you use the `login()` method instead of `token_auth()`, the JWT will be installed into the same client
right away. Many of the administrative Baserow APIs require a JWT (such as listing available applications,
i.e. databases, creating users, etc.).

__Examples:__

```py
for db in client.list_all_applications():
  print(db, [t.name for t in db.tables])

for table in client.list_database_tables(13):
  print(table)

for field in client.list_database_table_fields(45):
  print(field)
```

CRUD operations on tables can be performed with a long-lived API token that can be generated via Baserow UI
(there's an endpoint as well but the Python client does not currently provide it).

__Example:__

```py
is_john_smith = Column('field_281').equal('John Smith')
page = client.list_database_table_rows(45, filter=[is_john_smith])
print(page.results)

client.create_database_table_row(45, {
  'field_281': 'Alice Doe',
  'field_293': 'alice@doe.org',
})
```

> Try the the `paginate_database_table_rows()` method to conveniently iterate over all
> pages.
