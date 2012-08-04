from time import time
import os
from datetime import datetime
from contextlib import contextmanager
from dateutil.tz import tzlocal
import pygit2
from gitmodel import exceptions

GIT_MODE_NORMAL     = 0o100633
GIT_MODE_EXECUTABLE = 0o100755
GIT_MODE_SYMLINK    = 0o120000
GIT_MODE_TREE       = 0o040000
GIT_MODE_COMMIT     = 0o160000

def get_object_by_path(tree, path):
    """
    Get the object from the given tree using the given path
    """
    path = path.strip(os.path.sep)
    parts = path.split(os.path.sep, 1)
    obj = tree[parts[0]].to_object()
    if len(parts) > 1 and obj.type == pygit2.GIT_OBJ_TREE:
        return get_object_by_path(obj, parts[1])
    return obj
    

class Repository(pygit2.Repository):
    """
    A wrapper a round pygit2.Repository which adds a few useful features when
    using git as a pure object database. Initialization occurs using a config
    object instead of a repo path.
    """
    def __init__(self, config):
        self._config = config
        repo_path = os.path.join(self._config.REPOSITORY_PATH, '.git')
        try:
            super(Repository, self).__init__(repo_path)
        except KeyError:
            msg = "Git repository not found at {}".format(repo_path)
            raise exceptions.RepositoryNotFound(msg)

    def build_path(self, path, entries=None, tree=None):
        """
        Builds out a tree path, starting with the leaf node, and updating all 
        trees up the parent chain, resulting in (potentially) a new OID for the
        root tree. 

        If ``tree`` is provided, the path will be built based off of that
        tree. Otherwise, it is built from an empty tree.

        If ``entries`` is provided, those entries are inserted (or updated)
        in the tree for the given path.
        
        The root tree OID is returned, so that it can be included in a commit 
        or stage. While the trees are written to the object db, they are not 
        read into the index, nor are they associated with any commmit or 
        reference. If you don't handle the returned OID in some way, it may 
        result in orphaned objects.
        """
        path = path.strip(os.path.sep)
        if path is not None and path != '':
            parent, name = os.path.split(path)
        else:
            parent, name = None, None
        
        # build tree
        tb_args = tree is not None and (tree,) or ()
        tb = self.TreeBuilder(*tb_args)
        for entry in entries:
            tb.insert(*entry)
        oid = tb.write()

        if parent is None:
            # we're at the root tree
            return oid

        entry = (name, oid, GIT_MODE_TREE)

        if parent == '':
            # parent is the root tree
            return self.build_path('', (entry,))

        return self.build_path(parent, (entry,))


    def create_commit(self, ref, tree, message='', author=None, committer=None, parents=None):
        """
        Create a commit with the given ref, tree, and message. If parent
        commits are not given, the commit pointed to by the given ref is used
        as the parent. If author and commitor are not given, the defaults in
        the config are used.
        """
        if not author:
            author = self._config.DEFAULT_GIT_USER
        if not committer:
            committer = author
        
        default_offset = self._config.get('DEFAULT_TZ_OFFSET', None)
        author = make_signature(*author, default_offset=default_offset)
        committer = make_signature(*committer, default_offset=default_offset)

        if parents is None:
            try:
                ref = self.lookup_reference(ref)
            except KeyError:
                parents = [] #initial commit
            else:
                parents = [ref.oid]
        
        # FIXME: create_commit updates the HEAD ref. This may lead to race
        # conditions. As long as HEAD isn't used for anything in the system, it
        # shouldn't be a problem.
        return super(Repository, self).create_commit(ref, author, committer, message, tree, parents)
    
    def get_tree(self, ref):
        """
        Returns the tree for a given branch (eg, refs/heads/master)
        """
        ref = self.lookup_reference(ref)
        return self[ref.oid].tree

    @contextmanager
    def lock(self, id):
        """
        Acquires a lock with the given id.
        """
        start_time = time()
        while self.locked(id):
            if time() - start_time > self._config.LOCK_WAIT_TIMEOUT:
                msg = "Lock wait timeout exceeded while trying to acquire lock '{}' on {}"
                msg = msg.format(id, self.path)
                raise exceptions.LockWaitTimeoutExceeded(msg)
            time.sleep(self._config.LOCK_WAIT_INTERVAL)

        # The blob itself is not important, just the fact that the ref exists
        emptyblob = self.create_blob('')
        ref = self.create_reference('refs/locks/{}'.format(id), emptyblob)
        yield
        ref.delete()

    def locked(self, id):
        try:
            self.lookup_reference('refs/locks/{}'.format(id))
        except KeyError:
            return False
        return True


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

        
