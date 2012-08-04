"""
Module for abstract serializer/unserializer base classes.
"""

from StringIO import StringIO

class SerializationError(Exception):
    """Something bad happened during serialization."""
    pass

class DeserializationError(Exception):
    """Something bad happened during deserialization."""
    pass

class Serializer(object):
    """
    Abstract serializer base class.
    """

    def serialize(self, obj, **options):
        """
        Serialize a GitModel instance.
        """
        self.options = options

        self.stream = options.pop("stream", StringIO())
        self.selected_fields = options.pop("fields", None)

        self.start_serialization()
        for field in obj._meta.fields:
            if field.serialize:
                if self.selected_fields is None or field.attname in self.selected_fields:
                    self.handle_field(obj, field)
        self.end_serialization()
        return self.getvalue()

    def get_string_value(self, obj, field):
        """
        Convert a field's value to a string.
        """
        return field.value_to_string(obj)

    def start_serialization(self):
        """
        Called when serializing of the object starts.
        """
        raise NotImplementedError

    def end_serialization(self):
        """
        Called when serializing of the object ends.
        """
        pass

    def handle_field(self, obj, field):
        """
        Called to handle each individual (non-relational) field on an object.
        """
        raise NotImplementedError

    def handle_fk_field(self, obj, field):
        """
        Called to handle a ForeignKey field.
        """
        raise NotImplementedError

    def handle_m2m_field(self, obj, field):
        """
        Called to handle a ManyToManyField.
        """
        raise NotImplementedError

    def getvalue(self):
        """
        Return the fully serialized object (or None if the output stream is
        not seekable).
        """
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

class Deserializer(object):
    """
    Abstract base deserializer class.
    """

    def __init__(self, model_class, **options):
        self.options = options
        self.model_class = model_class

    def deserialize(self, data):
        raise NotImplementedError
