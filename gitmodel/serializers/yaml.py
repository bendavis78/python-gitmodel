"""
YAML serializer.

Requires PyYaml (http://pyyaml.org/), but that's checked for in __init__.
"""

import decimal
import yaml
from gitmodel.serializers.python import Serializer as PythonSerializer
from gitmodel.serializers.python import Deserializer as PythonDeserializer
from gitmodel import fields

class SafeDumper(yaml.SafeDumper):
    def represent_decimal(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', str(data))

SafeDumper.add_representer(decimal.Decimal, SafeDumper.represent_decimal)

class Serializer(PythonSerializer):
    """
    Convert an object to YAML.
    """
    def handle_field(self, obj, field):
        # A nasty special case: base YAML doesn't support serialization of time
        # types (as opposed to dates or datetimes, which it does support). Since
        # we want to use the "safe" serializer for better interoperability, we
        # need to do something with those pesky times. Converting 'em to strings
        # isn't perfect, but it's better than a "!!python/time" type which would
        # halt deserialization under any other language.
        if isinstance(field, fields.TimeField) and getattr(obj, field.name) is not None:
            self._current[field.name] = str(getattr(obj, field.name))
        else:
            super(Serializer, self).handle_field(obj, field)

    def end_serialization(self):
        yaml.dump(self.objects, self.stream, Dumper=SafeDumper, **self.options)

class Deserializer(PythonDeserializer):
    def deserialize(self, data):
        """
        Deserialize a string of YAML data.
        """
        python_data = yaml.load(data)
        return super(Deserializer, self).deserialize(python_data)
