# TODO: try to load faster json libraries that might be available, eg,
# simplejson, yajl

try:
    import cjson as json
except ImportError:
    import json  # flake8: noqa
