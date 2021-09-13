# baserow-client

A Python client for [Baserow.io](https://baserow.io/) with simple ORM capabilities.

> __Note__: This package is currently under development. Some APIs may break without prior notice.

__Installation__

    $ pip install baserow-client

## Getting started

### `BaserowClient`

The Baserow client provides direct access to many of the Baserow API endpoints. It must be initialized with
the URL to your Baserow instance as well as a JWT or Token. Without authentication, the client may still be
used to generate a JWT from user credentials.

```py
from baserow.client import BaserowClient

client = BaserowClient('https://baserow.io', jwt='...')
client = BaserowClient('https://baserow.io', token='...')

client = BaserowClient('https://baserow.io')
user, jwt = client.token_auth('username', 'password')
```

If you use the `login()` method instead of `token_auth()`, the JWT will be installed into the same client
right away.

### Operations that require a JWT

Meta operations such as listing available applications, tables, fields or creating/updating/deleting databases,
etc. require a JWT.

__Examples__

```py
for db in client.list_all_applications():
  print(db, [t.name for t in db.tables])

for table in client.list_database_tables(13):
  print(table)

for field in client.list_database_table_fields(45):
  print(field)
```

### Create/Read/Update/Delete rows

These operations do not require a JWT and can be performed with a long-lived token instead, which can be created
from the Baserow UI. The Baserow Python client currently supports reading data only.

__Example__

```py
is_john_smith = Column('field_281').equal('John Smith')
page = client.list_database_table_rows(45, filter=[is_john_smith])
print(page.results)
```

You can use the `paginate_database_table_rows()` convenience method to receive an iterator for all pages.

### Object-relational mapper

The Baserow Python client comes with basic ORM capabilities.

> __Note__: The ORM API is not Mypy compatible. Support _could_ be added by implementing a Mypy plugin.

__Define models__

```py
# myapp/models.py

from baserow.orm import Column, ForeignKey, Model

class Product(Model):
  name = Column('Name')
  price = Column('Price')

class Customer(Model):
  name = Column('Name')
  favorite_products = ForeignKey('Favorite Products', Product)
```

__Generate a database mapping__

Because the database schema cannot be introspected using a normal token, it is necessary to generate a mapping for
the ORM using a JWT. The easiest way to do this is to use the Baserow ORM command-line interface.

    $ python -m baserow.orm \
        'My web shop' myapp.models.Product:Produces myapp.models.Customer:Customers \
        --url https://baserow.io --user my-email@example.org --write-to var/conf/mapping.json

You can specify `--password '...'` to avoid the password prompt, or directly pass a JWT with `--jwt '...'`.

__Database connection__

The database connection must be initialized with a Baserow client and the database mapping that was generated
in the previous step. Since the ORM can only perform CRUD operations, a long-lived token can (or should) be used.

```py
# myapp/__main__.py

from baserow.client import BaserowClient
from baserow.orm import Database, DatabaseMapping
from .models import Product, Customer

client = BaserowClient('https://baserow.io', token='...')
db = Database(client, DatabaseMapping.load('var/data/mapping.json'))
```

__ORM queries__

When querying rows from Baserow with the ORM interface, you are working with instances of the `Model` subclasses
that you have defined previously. Linked rows are queried lazily (i.e. iterating over `Customer.favorite_products`
will fetch each linked `Product` from Baserow).

```py
query = db.select(Customer).filter(Customer.name.contains('Alice'))

print('Alice likes:')
for product in query.first().favorite_products:
  print(f'- {product.name}')
```

> Note: Fetching linked rows currently happens individually and can thus be rather slow. More information at
> [baserow#601](https://gitlab.com/bramw/baserow/-/issues/601). You can still access the raw `(id, name)` pairs
> returned by the Baserow API for the original object via `alice.favorite_products.raw`).

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
