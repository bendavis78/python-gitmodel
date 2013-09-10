import copy
import decimal
import os
import re
import uuid
from datetime import datetime, date, time
from StringIO import StringIO
from urlparse import urlparse

import pygit2

from gitmodel.utils import isodate, json
from gitmodel.exceptions import ValidationError, FieldError

INVALID_PATH_CHARS = ('/', '\000')


class NOT_PROVIDED:
    def __str__(self):
        return 'No default provided.'


class Field(object):
    """The base implementation of a field used by a GitModel class."""
    creation_counter = 0
    default_error_messages = {
        'required': 'is required',
        'invalid_path': 'may only contain valid path characters',
    }
    serializable = True
    empty_value = None

    def __init__(self, name=None, id=False, default=NOT_PROVIDED,
                 required=True, readonly=False, unique=False, serialize=True,
                 autocreated=False, error_messages=None):

        self.model = None
        self.name = name
        self.id = id
        self._default = default
        self.required = required
        self.readonly = readonly
        self.value = self.empty_value
        self.unique = unique
        self.serializeable = self.serializable and serialize
        self.autocreated = autocreated

        # update error_messages using default_error_messages from all parents
        #NEEDS-TEST
        messages = {}
        for c in reversed(type(self).__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

        # store the creation index in the "creation_counter" of the field
        self.creation_counter = Field.creation_counter
        # increment the global counter
        Field.creation_counter += 1

    def contribute_to_class(self, cls, name):
        field = self
        field.name = name
        # if this field has already been assigned to a model, assign a shallow
        # copy of it instead.
        if field.model:
            field = copy.copy(field)
        field.model = cls
        cls._meta.add_field(field)

    def has_default(self):
        """Returns a boolean of whether this field has a default value."""
        return self._default is not NOT_PROVIDED

    @property
    def default(self):
        """Returns the default value for the field."""
        if self.has_default():
            if callable(self._default):
                return self._default()
            return self._default
        return

    def empty(self, value):
        """Returns True if value is considered an empty value for this field"""
        return value is None or value == self.empty_value

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)

    def to_python(self, value):
        """
        Coerces the data into a valid python value. Raises ValidationError if
        the value cannot be coerced.
        """
        return value

    def get_raw_value(self, model_instance):
        """
        Used during the model's clean_fields() method. There is usually no
        need to override this unless the field is a descriptor.
        """
        return getattr(model_instance, self.name)

    def validate(self, value, model_instance):
        """
        Validates a coerced value (ie, passed through to_python) and throws a
        ValidationError if invalid.
        """
        if self.required and self.empty(value):
            raise ValidationError('required', self)

        if self.id and any(c in value for c in INVALID_PATH_CHARS):
            raise ValidationError('invalid_path', self)

    def clean(self, value, model_instance):
        """
        Validates the given value and returns its "cleaned" value as an
        appropriate Python object.

        Raises ValidationError for any errors.
        """
        value = self.to_python(value)
        self.validate(value, model_instance)
        return value

    def serialize(self, obj):
        """
        Returns a python value used for serialization.
        """
        value = getattr(obj, self.name)
        return self.to_python(value)

    def deserialize(self, data, value):
        """
        Returns the proper value just after deserialization
        """
        return self.to_python(value)

    def get_error_message(self, error_code, default='', **kwargs):
        msg = self.error_messages.get(error_code, default)
        kwargs['field'] = self
        msg = msg.format(**kwargs)
        return '"{name}" {err}'.format(name=self.name, err=msg)

    def post_save(self, value, model_instance, commit=False):
        """
        Called after the model has been saved, just before it is committed.
        The commit argument is passed through from GitModel.save()
        """
        pass


class CharField(Field):
    """
    A text field of arbitrary length.
    """
    empty_value = ''

    def to_python(self, value):
        if value is None and not self.required:
            return self.empty_value

        if value is None:
            return None

        return unicode(value)


class SlugField(CharField):
    default_error_messages = {
        'invalid_slug': ('must contain only letters, numbers, underscores and '
                         'dashes')
    }

    def validate(self, value, model_instance):
        super(SlugField, self).validate(value, model_instance)
        slug_re = re.compile(r'^[-\w]+$')
        if not slug_re.match(value):
            raise ValidationError('invalid_slug', self)


class EmailField(CharField):
    default_error_messages = {
        'invalid_email': 'must be a valid e-mail address'
    }

    def validate(self, value, model_instance):
        super(EmailField, self).validate(value, model_instance)

        email_re = re.compile(
            r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+"
            r"(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]'
            r'|\\[\001-011\013\014\016-\177])*"'  # quoted-string
            r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}'
            r'[A-Z0-9])?\.)+[A-Z]{2,6}\.?$',  # domain
            re.IGNORECASE)

        if not email_re.match(value):
            raise ValidationError('invalid_email', self)


class URLField(CharField):
    default_error_messages = {
        'invalid_url': 'must be a valid URL',
        'invalid_scheme': 'scheme must be one of {schemes}'
    }

    def __init__(self, **kwargs):
        """
        ``schemes`` is a list of URL schemes to which this field should be
        restricted. Raises validation error if url scheme is not in this list.
        Otherwise, any scheme is allowed.
        """
        self.schemes = kwargs.pop('schemes', None)
        super(URLField, self).__init__(self, **kwargs)

    def validate(self, value, model_instance):
        super(URLField, self).validate(value, model_instance)
        if self.empty(value):
            return
        parsed = urlparse(value)
        if not all((parsed.scheme, parsed.hostname)):
            raise ValidationError('invalid_url', self)
        if self.schemes and parsed.scheme.lower() not in self.schemes:
            schemes = ', '.join(self.schemes)
            raise ValidationError('invalid_scheme', self, schemes=schemes)


class BlobFieldDescriptor(object):
    def __init__(self, field):
        self.field = field
        self.data = None

    def __get__(self, instance, instance_type=None):
        if self.data is None:
            workspace = instance._meta.workspace
            path = self.field.get_data_path(instance)
            try:
                blob = workspace.index[path].oid
            except KeyError:
                return None
            self.data = StringIO(workspace.repo[blob].data)
        return self.data

    def __set__(self, instance, value):
        if isinstance(value, type(self)):
            # re-set data to read from repo on next __get__
            self.data = None
        elif value is None:
            self.data = None
        elif hasattr(value, 'read'):
            self.data = StringIO(value.read())
        else:
            self.data = StringIO(value)


class BlobField(Field):
    """
    A field for storing larger amounts of data with a model. This is stored as
    its own git blob within the repository, and added as a file entry under the
    same path as the data.json for that instance.
    """
    serializable = False

    def to_python(self, value):
        if hasattr(value, 'read'):
            return value
        if value is None:
            return None
        return StringIO(value)

    def post_save(self, value, instance, commit=False):
        if value is None:
            return
        workspace = instance._meta.workspace
        path = self.get_data_path(instance)
        # the value should already be coerced to a file-like object by now
        content = value.read()
        workspace.add_blob(path, content)

    def get_data_path(self, instance):
        path = os.path.dirname(instance.get_data_path())
        path = os.path.join(path, self.name)
        return '{0}.data'.format(path)

    def contribute_to_class(self, cls, name):
        super(BlobField, self).contribute_to_class(cls, name)
        setattr(cls, name, BlobFieldDescriptor(self))

    def deserialize(self, data, value):
        return BlobFieldDescriptor(self)


class IntegerField(Field):
    """
    An integer field.
    """
    default_error_messages = {
        'invalid_int': 'must be an integer'
    }

    def to_python(self, value):
        if value is None:
            return None
        # we should only allow whole numbers. so we coerce to float first, then
        # check to see if it's divisible by 1 without a remainder
        try:
            value = float(value)
        except ValueError:
            raise ValidationError('invalid_int', self)
        if value % 1 != 0:
            raise ValidationError('invalid_int', self)
        return int(value)


class UUIDField(CharField):
    """
    A CharField which uses a globally-unique identifier as its default value
    """
    @property
    def default(self):
        return uuid.uuid4().hex


class FloatField(Field):
    default_error_messages = {
        'invalid_float': 'must be a floating-point number'
    }

    def to_python(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            raise ValidationError('invalid_float', self)


class DecimalField(Field):
    default_error_messages = {
        'invalid_decimal': 'must be a numeric value',
    }

    def __init__(self, max_digits=None, decimal_places=None, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        super(DecimalField, self).__init__(**kwargs)

    def to_python(self, value):
        if value is None:
            return None
        if type(value) == float:
            value = str(value)
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise ValidationError('invalid_decimal', self)


class BooleanField(Field):
    def __init__(self, nullable=False, **kwargs):
        self.nullable = nullable
        super(BooleanField, self).__init__(**kwargs)

    def to_python(self, value):
        if value is None and self.nullable:
            return None
        return bool(value)


class DateField(Field):
    default_error_messages = {
        'invalid_format': 'must be in the format of YYYY-MM-DD',
        'invalid': 'must be a valid date',
    }

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        if isinstance(value, basestring):
            try:
                return isodate.parse_iso_date(value)
            except isodate.InvalidFormat:
                raise ValidationError('invalid_format', self)
            except isodate.InvalidDate:
                raise ValidationError('invalid', self)


class DateTimeField(Field):
    default_error_messages = {
        'invalid_format': 'must be in the format of YYYY-MM-DD HH:MM[:SS]',
        'invalid': 'must be a valid date/time'
    }

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day)

        if isinstance(value, basestring):
            try:
                return isodate.parse_iso_datetime(value)
            except isodate.InvalidFormat:
                # we also accept a date-only string
                try:
                    return isodate.parse_iso_date(value)
                except isodate.InvalidFormat:
                    raise ValidationError('invalid_format', self)
            except isodate.InvalidDate:
                raise ValidationError('invalid', self)


class TimeField(Field):
    default_error_messages = {
        'invalid_format': 'must be in the format of HH:MM[:SS]',
        'invalid': 'must be a valid time'
    }

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, time):
            return value

        if isinstance(value, basestring):
            try:
                return isodate.parse_iso_time(value)
            except isodate.InvalidFormat:
                raise ValidationError('invalid_format', self)
            except isodate.InvalidDate:
                raise ValidationError('invalid', self)


class RelatedFieldDescriptor(object):
    def __init__(self, field):
        self.field = field
        self.id = None

    def __get__(self, instance, instance_type=None):
        from gitmodel import models
        if instance is None:
            return self
        value = instance.__dict__[self.field.name]
        if value is None or isinstance(value, models.GitModel):
            return value
        return self.field.to_model.get(value)

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = value


class RelatedField(Field):
    def __init__(self, model, **kwargs):
        self._to_model = model
        super(RelatedField, self).__init__(**kwargs)

    @property
    def to_model(self):
        if not self.workspace:
            return self._to_model

        # if to_model is a string, it must be registered on the same workspace
        if isinstance(self._to_model, basestring):
            if not self.workspace.models.get(self._to_model):
                msg = "Could not find model '{0}'".format(self._to_model)
                raise FieldError(msg)
            return self.workspace.models[self._to_model]

        # if the model has already been registered with a workspace, use as-is
        if hasattr(self._to_model, '_meta'):
            return self._to_model

        # otherwise, check on our own workspace
        if self.workspace.models.get(self._to_model.__name__):
            return self.workspace.models[self._to_model.__name__]

        # if it's a model but hasn't been registered, register it on the same
        # workspace.
        return self.workspace.register_model(self.to_model)

    def to_python(self, value):
        from gitmodel import models
        if isinstance(value, models.GitModel):
            return value.get_id()
        return value

    def serialize(self, obj):
        value = obj.__dict__[self.name]
        return self.to_python(value)

    def contribute_to_class(self, cls, name):
        super(RelatedField, self).contribute_to_class(cls, name)
        if hasattr(cls, '_meta'):
            self.workspace = cls._meta.workspace
        setattr(cls, name, RelatedFieldDescriptor(self))


class GitObjectFieldDescriptor(object):
    def __init__(self, field):
        self.field = field
        self.oid = None

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self
        value = instance.__dict__[self.field.name]
        if value is None or isinstance(value, pygit2.Object):
            return value
        return instance._meta.workspace.repo[value]

    def __set__(self, instance, value):
        if isinstance(value, pygit2.Object):
            value = value.oid.hex
        elif isinstance(value, pygit2.Oid):
            value = value.hex
        instance.__dict__[self.field.name] = value


class GitObjectField(CharField):
    """
    Acts as a reference to a git object. This field stores the OID of the
    object. Returns the actual object when accessed as a property.
    """
    default_error_messages = {
        'invalid_oid': "must be a valid git OID or pygit2 Object",
        'invalid_type': "must point to a {type}",
    }

    def __init__(self, **kwargs):
        """
        If ``type`` is given, restricts the field to a specific type, and will
        raise a ValidationError during .validate() if an invalid type is given.

        ``type`` can be a valid pygit2 git object class, such as pygit2.Blob,
        pygit2.Commit, or pygit2.Tree. Any object type that can be resolved
        from a git oid is valid.
        """
        self.type = kwargs.pop('type', None)
        super(GitObjectField, self).__init__(**kwargs)

    def to_python(self, value):
        if not isinstance(value, (basestring, pygit2.Oid, pygit2.Object)):
            raise ValidationError('invalid_object', self)
        if isinstance(value, pygit2.Oid):
            return value.hex
        return value

    def clean(self, value, model_instance):
        raw_value = model_instance.__dict__[self.name]
        return super(GitObjectField, self).clean(raw_value, model_instance)

    def serialize(self, obj):
        value = obj.__dict__[self.name]
        return self.to_python(value)

    def contribute_to_class(self, cls, name):
        super(GitObjectField, self).contribute_to_class(cls, name)
        setattr(cls, name, GitObjectFieldDescriptor(self))

    def get_raw_value(self, model_instance):
        return model_instance.__dict__[self.name]

    def validate(self, value, model_instance):
        super(GitObjectField, self).validate(value, model_instance)
        oid = model_instance.__dict__[self.name]
        try:
            obj = model_instance._meta.workspace.repo[oid]
        except (ValueError, KeyError):
            raise ValidationError('invalid_oid', self)
        if self.type and not isinstance(obj, self.type):
            raise ValidationError('invalid_type', self,
                                  type=self.type.__name__)


class JSONField(CharField):
    def to_python(self, value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except ValueError, e:
            raise ValidationError(e)
