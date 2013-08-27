import fnmatch
import os
import re
import sys

import pygit2


__all__ = ['describe_tree', 'build_path', 'glob']


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


def describe_tree(repo, tree, indent=2, lvl=0):
    """
    Returns a string representation of the given tree, recursively.
    """
    output = []
    if isinstance(tree, pygit2.Oid):
        tree = repo[tree]
    for e in tree:
        i = ' ' * indent * lvl
        is_tree = repo[e.oid].type == pygit2.GIT_OBJ_TREE
        slash = is_tree and '/' or ''
        output.append('{}{}{}'.format(i, e.name, slash))
        if is_tree:
            sub_items = describe_tree(repo, e.oid, indent, lvl + 1)
            output.extend(sub_items)
    if lvl == 0:
        return '\n'.join(output)
    return output


def glob(repo, tree, pathname):
    """
    Return an iterator which yields the paths matching a pathname pattern.

    This is identical to python's glob.iglob() function, but works on the
    given git tree object instead of the filesystem.
    """
    if isinstance(tree, pygit2.Oid):
        tree = repo[tree]

    pathname = pathname.strip('/')
    if not has_magic(pathname):
        if path_exists(tree, pathname):
            yield pathname
        return

    dirname, basename = os.path.split(pathname)
    if not dirname:
        for name in glob1(repo, tree, os.curdir, basename):
            yield name
        return
    # `os.path.split()` returns the argument itself as a dirname if it is a
    # drive or UNC path.  Prevent an infinite recursion if a drive or UNC path
    # contains magic characters (i.e. r'\\?\C:').
    if dirname != pathname and has_magic(dirname):
        dirs = glob(repo, tree, dirname)
    else:
        dirs = [dirname]
    if has_magic(basename):
        glob_in_dir = glob1
    else:
        glob_in_dir = glob0
    for dirname in dirs:
        for name in glob_in_dir(repo, tree, dirname, basename):
            yield os.path.join(dirname, name)

# These 2 helper functions non-recursively glob inside a literal directory.
# They return a list of basenames. `glob1` accepts a pattern while `glob0`
# takes a literal basename (so it only has to check for its existence).


def glob1(repo, tree, dirname, pattern):
    if not dirname:
        dirname = os.curdir
    if isinstance(pattern, unicode) and not isinstance(dirname, unicode):
        dirname = unicode(dirname, sys.getfilesystemencoding() or
                          sys.getdefaultencoding())
    if dirname != os.curdir:
        try:
            tree = repo[tree[dirname].oid]
        except KeyError:
            return []
    names = [e.name for e in tree]
    if pattern[0] != '.':
        names = filter(lambda n: n[0] != '.', names)
    return fnmatch.filter(names, pattern)


def glob0(repo, tree, dirname, basename):
    if basename == '':
        # `os.path.split()` returns an empty basename for paths ending with a
        # directory separator.  'q*x/' should match only directories.
        if path_exists(tree, dirname):
            entry = tree[dirname]
            if repo[entry.oid].type == pygit2.GIT_OBJ_TREE:
                return [basename]
    else:
        if path_exists(tree, os.path.join(dirname, basename)):
            return [basename]
    return []


magic_check = re.compile('[*?[]')


def has_magic(s):
    return magic_check.search(s) is not None


def path_exists(tree, path):
    try:
        tree[path]
    except KeyError:
        return False
    return True


def walk(repo, tree, topdown=True):
    """
    Similar to os.walk(), using the given tree as a reference point.
    """
    names = lambda entries: [e.name for e in entries]

    dirs, nondirs = [], []
    for e in tree:
        is_tree = repo[e.oid].type == pygit2.GIT_OBJ_TREE
        if is_tree:
            dirs.append(e)
        else:
            nondirs.append(e)

    if topdown:
        yield tree, names(dirs), names(nondirs)
    for entry in dirs:
        new_tree = repo[entry.oid]
        for x in walk(repo, new_tree, topdown):
            yield x
    if not topdown:
        yield tree, names(dirs), names(nondirs)
