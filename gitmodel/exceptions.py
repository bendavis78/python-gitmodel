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
