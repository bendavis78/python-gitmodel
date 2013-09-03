"""
A JSON GitModel Serializer, which serves as the default serializer for
GitModel objects.
"""

import datetime
import decimal
from StringIO import StringIO

from gitmodel.utils import json
from gitmodel.serializers import python


def serialize(obj, fields=None, stream=None, **options):
    """
    Serialize a GitModel object to JSON.

    fields: When None, serilizes all fields. Otherwise, only the given fields
            will be returned in the serialized output.

    stream: An optional file-like object that is passed to json.dump(). If not
            supplied, the entire JSON string will be returened. Otherwies, the
            stream object itself will be returned.

    options: Addition options to pass to json.dump()
    """
    return_string = False
    if not stream:
        return_string = True
        stream = StringIO()

    pyobj = python.serialize(obj, fields)

    json.dump(pyobj, stream, cls=GitModelJSONEncoder, **options)
    if return_string:
        return stream.getvalue()
    return stream


def deserialize(workspace, data, oid, **options):
    """
    Load a JSON object string as a GitModel instance.

    model: the model class representing the data

    data: a valid JSON string

    options: additional options to pass to json.loads()
    """
    data = json.loads(data, **options)
    return python.deserialize(workspace, data, oid)


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
            return float(o)
        else:
            return super(GitModelJSONEncoder, self).default(o)
