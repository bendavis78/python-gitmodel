import os
from time import time
from datetime import datetime
from dateutil.tz import tzlocal
import pygit2

def make_signature(name, email, timestamp=None, offset=None, default_offset=None):
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

def describe_tree(repo, tree, indent=2, lvl=0):
    """
    Returns a string representation of the given tree, recursively.
    """
    output = []
    tree = repo[tree]
    for e in tree:
        i = ' ' * indent * lvl
        is_tree = repo[e.oid].type == pygit2.GIT_OBJ_TREE
        slash = is_tree and '/' or ''
        output.append('{}{}{}'.format(i, e.name, slash))
        if is_tree:
            sub_items = describe_tree(repo, e.oid, indent, lvl+1)
            output.extend(sub_items)
    if lvl == 0:
        return '\n'.join(output)
    return output

def build_path(repo, path, entries=None, root=None):
    """
    Builds out a tree path, starting with the leaf node, and updating all 
    trees up the parent chain, resulting in (potentially) a new OID for the
    root tree. 

    If ``entries`` is provided, those entries are inserted (or updated)
    in the tree for the given path.

    If ``root`` is provided, the path will be built based off of that
    tree. Otherwise, it is built off of an empty tree. Accepts an OID or a
    pygit2.Tree object.
    
    The root tree OID is returned, so that it can be included in a commit 
    or stage.
    """
    path = path.strip(os.path.sep)
    if path is not None and path != '':
        parent, name = os.path.split(path)
    else:
        parent, name = None, None
    
    if root is None:
        # use an empty tree
        root_id = repo.TreeBuilder().write()
        root = repo[root_id]

    if isinstance(root, (basestring, pygit2.Oid)):
        root = repo[root]

    if parent is None:
        # we're at the root tree
        tb_args = (root.oid,)
    else:
        # see if current path exists 
        try:
            tree = root[path]
        except KeyError:
            tb_args = ()
        else:
            tb_args = (tree.oid,)

    # build tree
    tb = repo.TreeBuilder(*tb_args)

    for entry in entries:
        tb.insert(*entry)
    oid = tb.write()

    if parent is None:
        # we're at the root tree
        return oid

    entry = (name, oid, pygit2.GIT_FILEMODE_TREE)

    if parent == '':
        # parent is the root tree
        return build_path(repo, '', (entry,), root)

    return build_path(repo, parent, (entry,), root)
