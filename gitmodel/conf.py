DEFAULTS = {
    'DEFAULT_BRANCH': 'refs/heads/master',
    'DEFAULT_SERIALIZER': 'json',
    'LOCK_WAIT_TIMEOUT': 30, # in seconds
    'LOCK_WAIT_INTERVAL': 1000, # in milliseconds
    'DEFAULT_GIT_USER': ('gitmodel', 'gitmodel@local'),
}

class Config(dict):
    def __init__(self, defaults=None):
        if defaults is None:
            defaults = {}
        final_defaults = DEFAULTS.copy()
        final_defaults.update(DEFAULTS)
        super(Config, self).__init__(final_defaults)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            msg = "'{}' object has no attribute '{}'"
            raise AttributeError(msg.format(self.__class__.__name__, name))

    def __setattr__(self, name, value):
        self[name] = value


# gitmodel.config.gloabl_settings are used as the default __config__ for
# GitModel classes, but this can be overridden to allow for individual
# config objects.
global_settings = Config()
