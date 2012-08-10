from time import time
import os
from contextlib import contextmanager
import pygit2
from gitmodel import conf
from gitmodel import exceptions
from gitmodel import models
from gitmodel.utils.git import make_signature

GIT_MODE_NORMAL     = 0o100633
GIT_MODE_EXECUTABLE = 0o100755
GIT_MODE_SYMLINK    = 0o120000
GIT_MODE_TREE       = 0o040000
GIT_MODE_COMMIT     = 0o160000

class Repository(object):
    """
    A Git repository. Acts as an encapsulation within which any model work is 
    done. This class does not make use of the repository's INDEX and HEAD 
    files, and instead keeps track of the these in memory.
    """
    def __init__(self, repo_path):
        self.config = conf.Config()
        try:
            self._repo = pygit2.Repository(repo_path)
        except KeyError:
            msg = "Git repository not found at {}".format(repo_path)
            raise exceptions.RepositoryNotFound(msg)
        
        # set default head
        self.head = self.config.DEFAULT_BRANCH
         
        # Set branch to head. If it the branch (head commit) doesn't exist, set
        # index to a new empty tree.
        try:
            self._repo.lookup_reference(self.head)
        except KeyError:
            oid = self._repo.TreeBuilder().write()
            self.index = self._repo[oid]
        else:
            self.update_index(self.head)

        # Create a base GitModel that can be easily extended
        metaclass = models.DeclarativeMetaclass
        attrs = {
            '__repo__': self,
            '__module__': __name__
        }
        self.GitModel = metaclass('GitModel', (models.GitModel,), attrs)

    def __getitem__(self, key):
        return self._repo[key]

    def create_blob(self, content):
        return self._repo.create_blob(content)

    def set_branch(self, name):
        """Sets the current head ref to the given branch name"""
        self.head = 'refs/heads/{}'.format(name)

    @property
    def branch(self):
        try:
            return self._repo.lookup_reference(self.head)
        except KeyError:
            return None

    def update_index(self, ref=None):
        """Sets the index to the current branch or to the given ref"""
        #NEEDS-TEST
        # Don't change the index if there are pending changes.
        if self.has_changes():
            msg = "Cannot checkout a different branch with pending changes"
            raise exceptions.RepositoryError(msg)
        self.head = ref
        if not self.branch:
            msg = "Pathspec {} did not match any files known to git".format(ref)
            raise exceptions.RepositoryError(msg)
        self.index = self.branch.commit.tree

    def add(self, path, entries):
        """
        Updates the current index given a path and a list of entries
        """
        #NEEDS-TEST
        oid = self.build_path(path, entries, self.index)
        self.index = self._repo[oid]

    def add_blob(self, path, content, mode=GIT_MODE_NORMAL):
        """
        Creates a blob object and adds it to the current index
        """
        blob = self._repo.create_blob(content)
        path, name = os.path.split(path)
        entry = (name, blob, mode)
        self.add(path, [entry])
        return blob

    def build_path(self, path, entries=None, tree=None):
        """
        Builds out a tree path, starting with the leaf node, and updating all 
        trees up the parent chain, resulting in (potentially) a new OID for the
        root tree. 

        If ``entries`` is provided, those entries are inserted (or updated)
        in the tree for the given path.

        If ``tree`` is provided, the path will be built based off of that
        tree. Otherwise, it is built off of the repo's current tree.
        
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
        tb = self._repo.TreeBuilder(*tb_args)
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

    @contextmanager
    def commit_on_success(self, message='', author=None, committer=None):
        """
        A context manager that allows you to wrap a block of changes and 
        commit those changes if no exceptions occur. This also ensures that
        the repository is in a clean state (i.e., no changes) before allowing
        any further changes.
        """
        #NEEDS-TEST
        # ensure a clean state
        if self.has_changes():
            msg = "Repository has pending changes. Cannot auto-commit until "\
                  "pending changes have been comitted."
            raise exceptions.RepostoryError(msg)

        yield

        self.commit(message, author, committer)
    
    def diff(self):
        """
        Returns a pygit2.Diff object representing a diff between the current
        index and the current branch.
        """
        #NEEDS-TEST
        if self.branch:
            tree = self._repo[self.branch.oid].commit.tree
        else:
            empty_tree = self._repo.TreeBuilder().write()
            tree = self._repo[empty_tree]
        return self.index.diff(tree)

    def has_changes(self):
        """Returns True if the current tree differs from the current branch"""
        return len(self.diff().changes) > 0
    
    def commit(self, message='', author=None, committer=None):
        """Commits the current tree to the current branch."""
        #NEEDS-TEST
        if not self.has_changes():
            return None
        parents = []
        if self.branch:
            parents = [self.branch.commit]
        return self.create_commit(self.head, self.index, message, author, committer, parents)
       
    def create_commit(self, ref, tree, message='', author=None, committer=None, parents=None):
        """
        Create a commit with the given ref, tree, and message. If parent
        commits are not given, the commit pointed to by the given ref is used
        as the parent. If author and commitor are not given, the defaults in
        the config are used.
        """
        if not author:
            author = self.config.DEFAULT_GIT_USER
        if not committer:
            committer = author
        
        default_offset = self.config.get('DEFAULT_TZ_OFFSET', None)
        author = make_signature(*author, default_offset=default_offset)
        committer = make_signature(*committer, default_offset=default_offset)

        if parents is None:
            try:
                parent_ref = self._repo.lookup_reference(ref)
            except KeyError:
                parents = [] #initial commit
            else:
                parents = [parent_ref.oid]
        
        # FIXME: create_commit updates the HEAD ref. This may lead to race
        # conditions. As long as HEAD isn't used for anything in the system, it
        # shouldn't be a problem.
        return self._repo.create_commit(ref, author, committer, message, tree.oid, parents)
    
    @contextmanager
    def lock(self, id):
        """
        Acquires a lock with the given id. Uses an empty reference to store the
        lock state, eg: refs/locks/my-lock
        """
        start_time = time()
        while self.locked(id):
            if time() - start_time > self.config.LOCK_WAIT_TIMEOUT:
                msg = "Lock wait timeout exceeded while trying to acquire lock '{}' on {}"
                msg = msg.format(id, self.path)
                raise exceptions.LockWaitTimeoutExceeded(msg)
            time.sleep(self.config.LOCK_WAIT_INTERVAL)

        # The blob itself is not important, just the fact that the ref exists
        emptyblob = self.create_blob('')
        ref = self.create_reference('refs/locks/{}'.format(id), emptyblob)
        yield
        ref.delete()

    def locked(self, id):
        try:
            self._repo.lookup_reference('refs/locks/{}'.format(id))
        except KeyError:
            return False
        return True
