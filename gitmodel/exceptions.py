class GitModelError(Exception):
    """A base exception for other gitmodel-related errors."""
    pass


class ConfigurationError(GitModelError):
    """Raised during configuration errors"""
    pass


class UnsupportedFormat(GitModelError):
    """
    Raised when an unsupported serialization format is requested.
    """
    pass


class FieldError(GitModelError):
    """
    Raised when there is a configuration error with a ``Field``.
    """
    pass


class DoesNotExist(GitModelError):
    """
    Raised when the object in question can't be found.
    """
    pass


class RepositoryError(GitModelError):
    """
    Raises during an error while operating with the repository
    """
    pass


class RepositoryNotFound(GitModelError):
    """
    Raises when the repository doesn't exist
    """


class ValidationError(GitModelError):
    """
    Raised when an invalid value is encountered
    """
    def __init__(self, msg_or_code, field=None, **kwargs):
        self.field = field
        self.msg_or_code = msg_or_code
        if self.field:
            msg = self.field.get_error_message(msg_or_code,
                                               default=msg_or_code,
                                               **kwargs)
        else:
            msg = msg_or_code
        super(ValidationError, self).__init__(msg)


class IntegrityError(GitModelError):
    """
    Raised when a save results in duplicate values
    """
    pass


class ModelNotFound(Exception):
    """
    Raised during deserialization if the model class no longer exists
    """
    pass
