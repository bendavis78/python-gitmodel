"""
Serialize data to/from JSON
"""

import datetime
import decimal

from gitmodel.serializers.python import Serializer as PythonSerializer
from gitmodel.serializers.python import Deserializer as PythonDeserializer
from gitmodel.utils import json

class Serializer(PythonSerializer):
    """
    Convert a queryset to JSON.
    """
    internal_use_only = False

    def end_serialization(self):
        json.dump(self.object, self.stream, cls=GitModelJSONEncoder, **self.options)

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

class Deserializer(PythonDeserializer):
    def deserialize(self, data):
        """
        Deserialize a stream or string of JSON data.
        """
        python_data = json.loads(data, **self.options)
        return super(Deserializer, self).deserialize(python_data)

class GitModelJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types.
    """

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        elif isinstance(o, datetime.date):
            return o.isoformat().split('T')[0]
        elif isinstance(o, datetime.time):
            return o.isoformat()
        elif isinstance(o, decimal.Decimal):
            return str(o)
        else:
            return super(GitModelJSONEncoder, self).default(o)
