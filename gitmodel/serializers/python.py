"""
A Python GitModel Serializer. Handles serialization of GitModel objects to/from
native python dictionaries.
"""
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

from gitmodel.exceptions import ValidationError, ModelNotFound
from gitmodel.serializers import ABORT, SET_EMPTY, IGNORE


def serialize(obj, fields=None, invalid=ABORT):
    """
    Serialize a GitModel object to JSON.

    fields:  When None, serilizes all fields. Otherwise, only the given fields
             will be returned in the serialized output.

    invalid: If a field cannot be coerced into its respective data type, a
             ValidationError will be raised. When invalid is ABORT, this
             exception is re-raised. SET_EMPTY causes the value to be set to an
             empty value. IGNORE simply uses the current value. Note that
             serialization may still fail with IGNORE if a value is not
             serializable.
    """
    pyobj = OrderedDict({
        'model': obj._meta.model_name,
        'fields': {}
    })
    for field in obj._meta.fields:
        if fields is None or field.name in fields:
            if field.serializable:
                try:
                    value = field.serialize(obj)
                except ValidationError:
                    if invalid == SET_EMPTY:
                        value = field.empty_value
                    elif invalid == IGNORE:
                        value = getattr(obj, field.name)
                    else:
                        raise
                pyobj['fields'][field.name] = value

    return pyobj


def deserialize(workspace, data, oid, invalid=IGNORE):
    """
    Load a python dict as a GitModel instance.

    model: the model class representing the data

    data: a valid JSON string

    invalid: If a field cannot be coerced into its respective data type, a
             ``ValidationError`` will be raised. When ``invalid`` is ``ABORT``,
             this exception is re-raised. ``SET_EMPTY`` causes the value to be
             set to an empty value. ``IGNORE`` simply uses the raw value.
    """
    attrs = {'oid': oid}
    try:
        model = workspace.models[data['model']]
    except KeyError:
        raise ModelNotFound(data['model'])
    for field in model._meta.fields:
        value = data['fields'].get(field.name)
        # field.deserialize() calls field.to_python(). If a serialized value
        # cannot be coerced into the correct type for its field, just assign
        # the raw value.
        try:
            value = field.deserialize(data, value)
        except ValidationError:
            if invalid == SET_EMPTY:
                value = field.empty_value
            elif invalid == ABORT:
                raise
        attrs[field.name] = value
    return model(**attrs)
