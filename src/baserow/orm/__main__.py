
import argparse
import getpass
import importlib
import json
import typing as t

from ..client import BaserowClient
from .mapping import DatabaseMapping, ModelMappingDescription

parser = argparse.ArgumentParser()
parser.add_argument('dbname', help='The database name to use.')
parser.add_argument('models', nargs='+', help='One or more absolute model IDs and their Baserow table name separated by colons.')
parser.add_argument('--url', required=True, help='The URL to your Baserow instance.')
parser.add_argument('--user', help='The username to authenticate with.')
parser.add_argument('--password', help='The password for the given --user. If omitted, the password will be asked.')
parser.add_argument('--jwt', help='A JWT to use instead of generating a new one with --user and --password.')
parser.add_argument('--write-to', help='The path to write the generated mappings to. If not specified, will be stdout.')


def main():
  args = parser.parse_args()
  client = BaserowClient(args.url)

  if args.user:
    if not args.password:
      args.password = getpass.getpass(f'Password for {args.user}: ')
    client.login(args.user, args.password)
  elif args.jwt:
    client.jwt = args.jwt
  else:
    parser.error('need at least --user or --jwt')

  models = []
  for spec in args.models:
    model_id, table_name = spec.split(':')
    module_name, class_name = model_id.rpartition('.')[::2]
    module = importlib.import_module(module_name)
    model = getattr(module, class_name)
    models.append(ModelMappingDescription(model_id, model.__columns__, table_name, {}))

  mapping = DatabaseMapping.generate(client, args.dbname, *models)
  if args.write_to:
    mapping.save(args.write_to)
  else:
    print(json.dumps(mapping.to_json(), indent=2))


if __name__ == '__main__':
  main()
