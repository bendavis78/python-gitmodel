import datetime
import re
import uuid
from dateutil.parser import parse
from decimal import Decimal
from gitmodel.utils import datetime_safe
from gitmodel.exceptions import FieldError, ValidationError


class NOT_PROVIDED:
    def __str__(self):
        return 'No default provided.'


EMPTY_VALUES = (None, '', [], (), {})
INVALID_PATH_CHARS = ('/', '\000')
DATE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*?$')
DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}).*?$')


class Field(object):
    """The base implementation of a field used by git models."""
    help_text = ''
    empty_strings_allowed = False
    creation_counter = 0
    default_error_messages = {
        'blank': 'cannot be blank',
        'null': 'cannot be null',
        'invalid_path': 'may only contain valid path characters',
    }
    error_messages = {}

    def __init__(self, name=None, attribute=None, id=False, 
            default=NOT_PROVIDED, null=False, blank=False, readonly=False, 
            unique=False, help_text=None, serialize=True, autocreated=False):

        self._model = None
        self.name = name
        self.attribute = attribute
        self.id = id
        self._default = default
        self.null = null
        self.blank = blank
        self.readonly = readonly
        self.value = None
        self.unique = unique
        self.serialize = serialize
        self.autocreated = autocreated

        error_messages = self.default_error_messages
        error_messages.update(self.error_messages)
        self.error_messages = error_messages
        
        # store the creation index in the "creation_counter" of the field
        self.creation_counter = Field.creation_counter
        # increment the global counter
        Field.creation_counter += 1

        if help_text:
            self.help_text = help_text

    def contribute_to_class(self, cls, name):
        self.name = name
        self.attribute = self.attribute or name
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
        if not self.empty_strings_allowed:
            return None
        return 
    
    def _get_val_from_obj(self, obj):
        if obj is not None:
            return getattr(obj, self.name)
        else:
            return self.default

    def value_to_string(self, obj):
        return unicode(self._get_val_from_obj(obj))

    def to_python(self, value):
        """
        Handles conversion between the data found and the type of the field.

        Extending classes should override this method and provide correct
        data coercion.
        """
        return value

    def __cmp__(self, other):
        # This is needed because bisect does not take a comparison function.
        if isinstance(self, basestring) or isinstance(other, basestring):
            import ipdb; ipdb.set_trace()
        return cmp(self.creation_counter, other.creation_counter)

    def validate(self, value, model_instance):
        """
        Validates value and throws ValidationError. Subclasses should override
        this to provide validation logic.
        """
        if value is None and not self.null:
            raise ValidationError('null', self)

        if not self.blank and value in EMPTY_VALUES:
            raise ValidationError('blank', self)

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
        return 'The "{}" field {}'.format(msg)

class CharField(Field):
    """
    A text field of arbitrary length.
    """
    empty_strings_allowed = True
    help_text = 'Unicode string data. Ex: "Hello World"'

    def to_python(self, value):
        # if we don't allow null, but do allow blank, convert None to ''
        if value is None and self.blank and not self.null:
            return ''

        if value is None:
            return None

        return unicode(value)

class SlugField(CharField):
    error_messages = {
        'invalid_slug': 'must contain only letters, numbers, underscores and dashes'
    }
    def validate(self, value, model_instance):
        slug_re = re.compile(r'^[-\w]+$')
        if not slug_re.match(value):
            raise ValidationError('invalid_slug', self)

class EmailField(CharField):
    error_messages = {
        'invalid_email': 'must be a valid e-mail address'
    }
    def validate(self, value, model_instance):
        email_re = re.compile(
            r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
            r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain
        if not email_re.matches(value):
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
    help_text = 'Integer data. Ex: 3742'
    error_messages = {
        'invalid_int': 'must be an integer'
    }

    def to_python(self, value):
        if value is None:
            return None

        return int(value)

    def validate(self, value, model_instance):
        try:
            self.to_python(value)
        except ValueError:
            raise ValidationError('invalid_int', self)

class UUIDField(CharField):
    """
    A CharField which uses a globally-unique identifier as its default value
    """
    @property
    def default(self):
        return uuid.uuid4().hex

class FloatField(Field):
    """
    A floating point field.
    """
    help_text = 'Floating point numeric data. Ex: 26.73'
    error_messages = {
        'invalid_float': 'must be a floating-point number'
    }

    def to_python(self, value):
        if value is None:
            return None

        return float(value)

    def validate(self, value, model_instance):
        try:
            self.to_python(value)
        except ValueError:
            raise ValidationError('invalid_float', self)


class DecimalField(Field):
    """
    A decimal field.
    """
    help_text = 'Fixed precision numeric data. Ex: 26.73'
    error_messages = {
        'invalid_decimal': 'must be a decimal number'
    }

    def to_python(self, value):
        if value is None:
            return None

        return Decimal(value)

    def validate(self, value, model_instance):
        try:
            self.to_python(value)
        except ValueError:
            raise ValidationError('invalid_decimal', self)



class BooleanField(Field):
    """
    A boolean field.
    """
    help_text = 'Boolean data. Ex: True'

    def to_python(self, value):
        if value is None:
            return None

        return bool(value)

class DateField(Field):
    """
    A date field.
    """
    help_text = 'A date as a string. Ex: "2010-11-10"'

    def to_python(self, value):
        if value is None:
            return None

        #TODO move validation to validate() function
        if isinstance(value, basestring):
            match = DATE_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.date(int(data['year']), int(data['month']), int(data['day']))
            else:
                raise FieldError("Date provided to '%s' field doesn't appear to be a valid date string: '%s'" % (self.attname, value))

        return value


class DateTimeField(Field):
    """
    A datetime field.
    """
    help_text = 'A date & time as a string. Ex: "2010-11-10T03:07:43"'

    #TODO move validation to validate() function
    def to_python(self, value):
        if value is None:
            return None

        if isinstance(value, basestring):
            match = DATETIME_REGEX.search(value)

            if match:
                data = match.groupdict()
                return datetime_safe.datetime(int(data['year']), int(data['month']), int(data['day']), int(data['hour']), int(data['minute']), int(data['second']))
            else:
                raise FieldError("Datetime provided to '%s' field doesn't appear to be a valid datetime string: '%s'" % (self.attname, value))

        return value


class TimeField(Field):
    help_text = 'A time as string. Ex: "20:05:23"'

    def to_python(self, value):
        #TODO move validation to validate() function
        if isinstance(value, basestring):
            return self.to_time(value)
        return value

    def to_time(self, s):
        try:
            dt = parse(s)
        except ValueError, e:
            raise FieldError(str(e))
        else:
            return datetime.time(dt.hour, dt.minute, dt.second)

class RelatedField(Field):
    #TODO
   pass


class ToOneField(RelatedField):
    #TODO
    pass


class ToManyField(RelatedField):
    #TODO
    pass
