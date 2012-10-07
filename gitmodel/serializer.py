import datetime
import decimal
from gitmodel.utils import json
from StringIO import StringIO

def serialize(obj, stream=None, fields=None, **options):
    if not stream:
        stream = StringIO()
    pyobj = {}
    for field in obj._meta.fields:
        if fields is None or field.name in fields:
            value = getattr(obj, field.name)
            if field.serializable:
                pyobj[field.name] = field.serialize(obj, value)
    json.dump(pyobj, stream, cls=GitModelJSONEncoder, **options)
    return stream.getvalue()

def deserialize(model, data, **options):
    attrs = {}
    data = json.loads(data, **options)
    for field in model._meta.fields:
        value = data.get(field.name)
        attrs[field.name] = field.deserialize(data, value)
    return model(**attrs)

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
