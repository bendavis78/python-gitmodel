"""
Originally based off of django-tastypie's fields module. See the LICENSE file
included with this distribution for more info.
"""
import datetime
import re
import uuid
from dateutil.parser import parse
from decimal import Decimal
from gitmodel.utils import datetime_safe
from gitmodel.exceptions import FieldError


class NOT_PROVIDED:
    def __str__(self):
        return 'No default provided.'


DATE_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).*?$')
DATETIME_REGEX = re.compile('^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})(T|\s+)(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}).*?$')


class Field(object):
    """The base implementation of a field used by git models."""
    help_text = ''
    empty_strings_allowed = False
    creation_counter = 0

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
        return cmp(self.creation_counter, other.creation_counter)


class CharField(Field):
    """
    A text field of arbitrary length.
    """
    empty_strings_allowed = True
    help_text = 'Unicode string data. Ex: "Hello World"'

    def to_python(self, value):
        if value is None:
            return None

        return unicode(value)

class SlugField(CharField):
    #TODO
    pass

class EmailField(CharField):
    #TODO
    pass

class FileField(Field):
    """
    A file-related field.
    """

    def to_python(self, value):
        if value is None:
            return None

        try:
            # Try to return the URL if it's a ``File``, falling back to the string
            # itself if it's been overridden or is a default.
            return getattr(value, 'url', value)
        except ValueError:
            return None

class IntegerField(Field):
    """
    An integer field.
    """
    help_text = 'Integer data. Ex: 3742'

    def to_python(self, value):
        if value is None:
            return None

        return int(value)

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

    def to_python(self, value):
        if value is None:
            return None

        return float(value)


class DecimalField(Field):
    """
    A decimal field.
    """
    help_text = 'Fixed precision numeric data. Ex: 26.73'

    def to_python(self, value):
        if value is None:
            return None

        return Decimal(value)


class BooleanField(Field):
    """
    A boolean field.
    """
    help_text = 'Boolean data. Ex: True'

    def to_python(self, value):
        if value is None:
            return None

        return bool(value)


class ListField(Field):
    """
    A list field.
    """
    help_text = "A list of data. Ex: ['abc', 26.73, 8]"

    def to_python(self, value):
        if value is None:
            return None

        return list(value)


class DictField(Field):
    """
    A dictionary field.
    """
    help_text = "A dictionary of data. Ex: {'price': 26.73, 'name': 'Daniel'}"

    def to_python(self, value):
        if value is None:
            return None

        return dict(value)


class DateField(Field):
    """
    A date field.
    """
    help_text = 'A date as a string. Ex: "2010-11-10"'

    def to_python(self, value):
        if value is None:
            return None

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
