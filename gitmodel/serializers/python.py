"""
Serialize models to native python objects. Useful as a base for other
serializers
"""

import types
import datetime
from decimal import Decimal
from gitmodel.serializers import base

class Serializer(base.Serializer):
    """
    Serializes a QuerySet to basic Python objects.
    """

    internal_use_only = True

    def _is_protected_type(self, obj):
        return isinstance(obj, (
            types.NoneType,
            int, long,
            datetime.datetime, datetime.date, datetime.time,
            float, Decimal)
        )
    def start_serialization(self):
        self.object = {}

    def handle_field(self, obj, field):
        value = field._get_val_from_obj(obj)
        # Protected types (i.e., primitives like None, numbers, dates,
        # and Decimals) are passed through as is. All other values are
        # converted to string first.
        if self._is_protected_type(value):
            self.object[field.name] = value
        else:
            self.object[field.name] = field.value_to_string(obj)

    def getvalue(self):
        return self.object

class Deserializer(base.Deserializer):
    def deserialize(self, data):
        """
        Deserialize simple Python objects back into GitModel instances.
        """
        # Handle each field
        attrs = {}
        for (field_name, field_value) in data.iteritems():
            field = self.model_class._meta.get_field(field_name)
            attrs[field.name] = field.to_python(field_value)
        return self.model_class(**attrs)
