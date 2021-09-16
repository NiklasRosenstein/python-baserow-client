# Baserow ORM

The Baserow Python client comes with basic ORM capabilities.

> __Note__: The ORM API is not Mypy compatible. Support _could_ be added by implementing a Mypy plugin.

## Defining models

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

## Generating a database mapping

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

## Querying

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
> returned by the Baserow API for the ori

The `Database.save()` currently provides very naive implementation to save new or update existing rows. It does
not currently handle `single_select` and `link_row` fields properly.

```py
row = Product(id=None, name='Soy beans', price=1.99)
db.save(row)
print(row.id)
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
