# baserow-client

A Python client for [Baserow.io](https://baserow.io/) with simple ORM capabilities.

## Installation

    $ pip install baserow-client

## Quickstart (Direct API)

```py
from baserow.client import BaserowClient
from baserow.filter import Column

client = BaserowClient('https://baserow.io', jwt='<JWT>')

for database in client.list_all_applications():
  print(database, [t.name for t in database.tables])

for table in client.list_database_tables(13):
  print(table)

for field in client.list_database_table_fields(45):
  print(field)

# Reading data can be done with a token (no JWT necessary).
client = BaserowClient('https://baserow.io', token='<TOKEN>')

is_john_smith = Column('field_281').equal('John Smith')
for page in client.paginated_database_table_rows(45, filter=[is_john_smith]):
  for row in page.results:
    print(row)
```

## Quickstart (ORM)

```py
from baserow.client import BaserowClient
from baserow.orm import Column, Model, Database, DatabaseMapping

class Product(Model):
  name = Column('Name')
  price = Column('Price')

# Jwt only needed for generating a mapping, only specify one or the other.
client = BaserowClient('https://baserow.io', jwt='<JWT>', token='<TOKEN>')

if client.jwt:
  mapping = DatabaseMapping.generate(client, 'My web shop', Product.of('Products'))
  mapping.save('mapping.json')
else:
  mapping = DatabaseMapping.load('mapping.json')

db = Database(client, mapping)

for product in db.select(Product).filter(Product.name.contains('Shirt')):
  print(product)
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
