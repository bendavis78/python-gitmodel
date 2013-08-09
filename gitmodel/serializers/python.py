"""
A Python GitModel Serializer. Handles serialization of GitModel objects to/from
native python dictionaries.
"""


def serialize(obj, fields):
    """
    Serialize a GitModel object to JSON.

    fields: When None, serilizes all fields. Otherwise, only the given fields
            will be returned in the serialized output.
    """
    pyobj = {}
    for field in obj._meta.fields:
        if fields is None or field.name in fields:
            if field.serializable:
                pyobj[field.name] = field.serialize(obj)
    return pyobj


def deserialize(model, data):
    """
    Load a python dict as a GitModel instance.

    model: the model class representing the data

    data: a valid JSON string
    """
    attrs = {}
    for field in model._meta.fields:
        value = data.get(field.name)
        attrs[field.name] = field.deserialize(data, value)
    return model(**attrs)
