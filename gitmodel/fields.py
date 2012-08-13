import re
import uuid
import decimal
from datetime import datetime, date, time
from gitmodel.utils import isodate
from gitmodel.exceptions import ValidationError

class NOT_PROVIDED:
    def __str__(self):
        return 'No default provided.'

INVALID_PATH_CHARS = ('/', '\000')

class Field(object):
    """The base implementation of a field used by a GitModel class."""
    creation_counter = 0
    default_error_messages = {
        'required': 'is required',
        'invalid_path': 'may only contain valid path characters',
    }

    def __init__(self, name=None, id=False, default=NOT_PROVIDED,
            required=True, readonly=False, unique=False, serialize=True, 
            autocreated=False, error_messages=None):

        self._model = None
        self.name = name
        self.id = id
        self._default = default
        self.required = required
        self.readonly = readonly
        self.value = None
        self.unique = unique
        self.serialize = serialize
        self.autocreated = autocreated

        # update error_messages using default_error_messages from all parents
        #NEEDS-TEST
        messages = {}
        for c in reversed(self.__class__.__mro__):
            messages.update(getattr(c, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages


        # store the creation index in the "creation_counter" of the field
        self.creation_counter = Field.creation_counter
        # increment the global counter
        Field.creation_counter += 1

    def contribute_to_class(self, cls, name):
        self.name = name
        self.model = cls
        cls._meta.add_field(self)

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
    
    def _get_val_from_obj(self, obj):
        if obj is not None:
            return getattr(obj, self.name)
        else:
            return self.default

    def value_to_string(self, obj):
        return unicode(self._get_val_from_obj(obj))

    def empty(self, value):
        """Returns True if value is considered an empty value for this field"""
        return not value;

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        return cmp(self.creation_counter, other.creation_counter)

    def to_python(self, value):
        """
        Coerces the data into a valid python value. Raises ValidationError if
        the value cannot be coerced.
        """
        return value

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

    def get_error_message(self, error_code, default=''):
        msg = self.error_messages.get(error_code, default)
        return '"{name}" {err}'.format(name=self.name, err=msg)

class CharField(Field):
    """
    A text field of arbitrary length.
    """

    def to_python(self, value):
        if value is None and not self.required:
            return ''

        if value is None:
            return None

        return unicode(value)

class SlugField(CharField):
    default_error_messages = {
        'invalid_slug': 'must contain only letters, numbers, underscores and dashes'
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
            r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
            r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain
        if not email_re.match(value):
            raise ValidationError('invalid_email', self)


class FileField(CharField):
    """
    A file-related field. Stores file path used to retrieve the file from the
    configured storage backend
    """
    #TODO
    pass


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

    def empty(self, value):
        return value is None

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

    def empty(self, value):
        return value is None


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
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation:
            raise ValidationError('invalid_decimal', self)

    def empty(self, value):
        return value is None


class BooleanField(Field):

    def __init__(self, nullable=False, **kwargs):
        self.nullable = nullable
        super(BooleanField, self).__init__(**kwargs)

    def to_python(self, value):
        if value is None and self.nullable:
            return None
        return bool(value)
    
    def empty(self, value):
        return value is None



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

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            return ''
        else:
            return val.isoformat().split('T')[0]

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

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            return ''
        else:
            return val.isoformat().replace('T', ' ')

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

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            return ''
        else:
            return val.isoformat()

class RelatedField(Field):
    #TODO
   pass


class ToOneField(RelatedField):
    #TODO
    pass


class ToManyField(RelatedField):
    #TODO
    pass
