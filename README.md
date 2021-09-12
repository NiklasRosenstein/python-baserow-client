# baserow-client

A Python client for [Baserow.io](https://baserow.io/).

## Installation

    $ pip install baserow-client

## Example

```py
from baserow.client import BaserowClient
from baserow.filter import Column

client = BaserowClient('https://baserow.io', '<JWT_TOKEN>')

for database in client.list_all_applications():
  print(database, [t.name for t in database.tables])

for table in client.list_database_tables(13):
  print(table)

for field in client.list_database_table_fields(45):
  print(field)

is_john_smith = Column('field_281').equal('John Smith')
for page in client.paginated_database_table_rows(45, filter=[is_john_smith]):
  for row in page.results:
    print(row)
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
