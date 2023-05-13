
from databind.json import load, dump
from baserow.types import TableField
from baserow.field_types import TextTableField, NumberTableField, NumberType


def test__TableField__can_deserialize_into_union_subtypes() -> None:
    """
    Tests deserialization for various TableField subtypes.
    """

    text_field = TextTableField(42, 1, 'foo', 0, False, 'bar')
    text_field_data = {"type": "text", "id": 42, "table_id": 1, "name": "foo", "order": 0, "primary": False, "text_default": "bar"}
    assert dump(text_field, TableField) == text_field_data
    assert load(text_field_data, TableField) == text_field

    number_field = NumberTableField(42, 1, 'foo', 0, False, 2, False, NumberType.INTEGER)
    number_field_data = {"type": "number", "id": 42, "table_id": 1, "name": "foo", "order": 0, "primary": False, "number_decimal_places": 2, "number_negative": False, "number_type": "INTEGER"}
    assert dump(number_field, TableField) == number_field_data
    assert load(number_field_data, TableField) == number_field
