import sys
import json
from dateutil.tz import tzlocal
from datetime import datetime
from time import time

import pygit2

from . import path

# We disable c_make_encoder for python between versions 2.7 and 2.7.3, so that
# we can use collections.OrderedDict when encoding.
if 0x20700f0 <= sys.hexversion < 0x20703f0:
    json.encoder.c_make_encoder = None

__all__ = ['json', 'make_signature', 'path']


def make_signature(name, email, timestamp=None, offset=None,
                   default_offset=None):
    """
    Creates a pygit2.Signature while making time and offset optional. By
    default, uses current time, and local offset as determined by
    ``dateutil.tz.tzlocal()``
    """
    if timestamp is None:
        timestamp = time()

    if offset is None and default_offset is None:
        # Get local offset
        dt = datetime.fromtimestamp(timestamp)
        aware = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                         dt.second, dt.microsecond, tzinfo=tzlocal())
        seconds = aware.utcoffset().days * 86400
        seconds += aware.utcoffset().seconds
        offset = seconds / 60
    elif offset is None:
        offset = default_offset

    return pygit2.Signature(name, email, timestamp, offset)


def treeish_to_tree(repo, obj):
    try:
        obj = repo.revparse_single(obj)
    except:
        pass

    if isinstance(obj, pygit2.Commit):
        return obj.tree
    elif isinstance(obj, pygit2.Reference):
        oid = obj.resolve().target
        return repo[oid]
