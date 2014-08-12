from contextlib import contextmanager
from importlib import import_module
from time import time
import logging
import os

import pygit2

from gitmodel import conf
from gitmodel import exceptions
from gitmodel import models
from gitmodel import utils


class Workspace(object):
    """
    A workspace acts as an encapsulation within which any model work is done.
    It is analogous to a git working directory. It also acts as a "porcelain"
    layer to pygit2's "plumbing".

    In contrast to a working directory, this class does not make use of the
    repository's INDEX and HEAD files, and instead keeps track of the these in
    memory.

    Passing initial_branch will set the default head for the workspace.
    """
    def __init__(self, repo_path, initial_branch='refs/heads/master'):
        self.config = conf.Config()

        # set up a model registry
        class ModelRegistry(dict):
            """This class acts like a so-called AttrDict"""
            def __init__(self):
                self.__dict__ = self

        self.models = ModelRegistry()

        try:
            self.repo = pygit2.Repository(repo_path)
        except KeyError:
            msg = "Git repository not found at {}".format(repo_path)
            raise exceptions.RepositoryNotFound(msg)

        self.index = None

        # set default head
        self.head = initial_branch

        # Set branch to head. If it the branch (head commit) doesn't exist, set
        # index to a new empty tree.
        try:
            self.repo.lookup_reference(self.head)
        except KeyError:
            oid = self.repo.TreeBuilder().write()
            self.index = self.repo[oid]
        else:
            self.update_index(self.head)

        # add a base GitModel which can be extended if needed
        self.register_model(models.GitModel, 'GitModel')

        self.log = logging.getLogger(__name__)

    def register_model(self, cls, name=None):
        """
        Register a GitModel class with this workspace. A GitModel cannot be
        used until it is registered with a workspace. This does not alter the
        origingal class, but rather creates a "clone" which is bound to this
        workspace. If a model attribute requires special handling for the
        cloning, that object should define a "contribute_to_class" method.

        Note that when a GitModel with any RelatedFields is registered, its
        related models will be automatically registered with the same workspace
        if they have not already been registered with a workspace.
        """
        if not issubclass(cls, models.GitModel):
            raise TypeError("{0!r} is not a GitModel.".format(cls))

        if not name:
            name = cls.__name__

        if self.models.get(name):
            return self.models[name]

        if hasattr(cls, '_meta'):
            if cls._meta.workspace != self:
                msg = "{0} is already registered with a different workspace"
                raise ValueError(msg.format(cls.__name__))
            # class has already been created with _meta, so we just register
            # and return it.
            self.models[name] = cls
            return cls

        metaclass = models.DeclarativeMetaclass
        attrs = dict(cls.__dict__, **{
            '__workspace__': self,
        })
        if not attrs.get('__module__'):
            attrs['__module__'] == __name__

        if attrs.get('__dict__'):
            del attrs['__dict__']

        # the cloned model must subclass the original so as not to break
        # type-checking operations
        bases = [cls]

        # parents must also be registered with the workspace
        for base in cls.__bases__:
            if issubclass(base, models.GitModel) and \
                    not hasattr(base, '_meta'):
                base = self.models.get(name) or self.register_model(base)
            bases.append(base)

        # create the new class and attach it to the workspace
        new_model = metaclass(name, tuple(bases), attrs)
        self.models[name] = new_model
        return new_model

    def import_models(self, path_or_module):
        """
        Register all models declared within a given python module
        """
        if isinstance(path_or_module, basestring):
            mod = import_module(path_or_module)
        else:
            mod = path_or_module

        for name in dir(mod):
            item = getattr(mod, name)
            if isinstance(item, type) and \
                    issubclass(item, models.GitModel):
                self.register_model(item, name)

        return self.models

    def create_blob(self, content):
        return self.repo.create_blob(content)

    def create_branch(self, name, start_point=None):
        """
        Creates a head reference with the given name. The start_point argument
        is the head to which the new branch will point -- it may be a branch
        name, commit id, or tag name (defaults to current branch).
        """
        if not start_point:
            start_point = self.head
        start_point_ref = self.repo.lookup_reference(start_point)

        if start_point_ref.type != pygit2.GIT_OBJ_COMMIT:
            raise ValueError('Given reference must point to a commit')

        branch_ref = 'refs/heads/{}'.format(name)
        self.repo.create_reference(branch_ref, start_point_ref.target)

    def get_branch(self, ref_name):
        return Branch(self.repo, ref_name)

    def set_branch(self, name):
        """
        Sets the current head ref to the given branch name
        """
        # make sure the branch is a valid head ref
        ref = 'refs/heads/{}'.format(name)
        self.repo.lookup_reference(ref)
        self.update_index(ref)

    @property
    def branch(self):
        try:
            return self.get_branch(self.head)
        except exceptions.RepositoryError:
            return None

    def update_index(self, treeish):
        """Sets the index to the current branch or to the given treeish"""
        # Don't change the index if there are pending changes.
        if self.index and self.has_changes():
            msg = "Cannot checkout a different branch with pending changes"
            raise exceptions.RepositoryError(msg)

        tree = utils.treeish_to_tree(self.repo, treeish)

        if treeish.startswith('refs/heads'):
            # if treeish is a head ref, update head
            self.head = treeish
        else:
            # otherwise, we're in "detached head" mode
            self.head = None

        self.index = tree

    def add(self, path, entries):
        """
        Updates the current index given a path and a list of entries
        """
        oid = utils.path.build_path(self.repo, path, entries, self.index)
        self.index = self.repo[oid]

    def remove(self, path):
        """
        Removes an item from the index
        """
        parent, name = os.path.split(path)
        parent_tree = parent and self.index[parent] or self.index
        tb = self.repo.TreeBuilder(parent_tree.oid)
        tb.remove(name)
        oid = tb.write()
        if parent:
            path, parent_name = os.path.split(parent)
            entry = (parent_name, oid, pygit2.GIT_FILEMODE_TREE)
            oid = utils.path.build_path(self.repo, path, [entry], self.index)
        self.index = self.repo[oid]

    def add_blob(self, path, content, mode=pygit2.GIT_FILEMODE_BLOB):
        """
        Creates a blob object and adds it to the current index
        """
        path, name = os.path.split(path)
        blob = self.repo.create_blob(content)
        entry = (name, blob, mode)
        self.add(path, [entry])
        return blob

    @contextmanager
    def commit_on_success(self, message='', author=None, committer=None):
        """
        A context manager that allows you to wrap a block of changes and commit
        those changes if no exceptions occur. This also ensures that the
        repository is in a clean state (i.e., no changes) before allowing any
        further changes.
        """
        # ensure a clean state
        if self.has_changes():
            msg = "Repository has pending changes. Cannot auto-commit until "\
                  "pending changes have been comitted."
            raise exceptions.RepositoryError(msg)

        yield

        self.commit(message, author, committer)

    def diff(self):
        """
        Returns a pygit2.Diff object representing a diff between the current
        index and the current branch.
        """
        if self.branch:
            tree = self.branch.tree
        else:
            empty_tree = self.repo.TreeBuilder().write()
            tree = self.repo[empty_tree]
        return tree.diff_to_tree(self.index)

    def has_changes(self):
        """Returns True if the current tree differs from the current branch"""
        # As of pygit2 0.19, Diff.patch seems to raise a non-descript GitError
        # if there are  no changes, so we check the iterable length instead.
        return len(tuple(self.diff())) > 0

    def commit(self, message='', author=None, committer=None):
        """Commits the current tree to the current branch."""
        if not self.has_changes():
            return None
        parents = []
        if self.branch:
            parents = [self.branch.commit.oid]
        return self.create_commit(self.head, self.index, message, author,
                                  committer, parents)

    def create_commit(self, ref, tree, message='', author=None,
                      committer=None, parents=None):
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
        author = utils.make_signature(*author, default_offset=default_offset)
        committer = utils.make_signature(*committer,
                                         default_offset=default_offset)

        if parents is None:
            try:
                parent_ref = self.repo.lookup_reference(ref)
            except KeyError:
                parents = []  # initial commit
            else:
                parents = [parent_ref.oid]

        # FIXME: create_commit updates the HEAD ref. HEAD isn't used in
        # gitmodel, however it would be prudent to make sure it doesn't
        # get changed. Possibly need to just restore it after the commit
        return self.repo.create_commit(ref, author, committer, message,
                                       tree.oid, parents)

    def walk(self, sort=pygit2.GIT_SORT_TIME):
        """Iterate through commits on the current branch"""
        #NEEDS-TEST
        for commit in self.repo.walk(self.branch.oid, sort):
            yield commit

    @contextmanager
    def lock(self, id):
        """
        Acquires a lock with the given id. Uses an empty reference to store the
        lock state, eg: refs/locks/my-lock
        """
        start_time = time()
        while self.locked(id):
            if time() - start_time > self.config.LOCK_WAIT_TIMEOUT:
                msg = ("Lock wait timeout exceeded while trying to acquire "
                       "lock '{}' on {}").format(id, self.path)
                raise exceptions.LockWaitTimeoutExceeded(msg)
            time.sleep(self.config.LOCK_WAIT_INTERVAL)

        # The blob itself is not important, just the fact that the ref exists
        emptyblob = self.create_blob('')
        ref = self.repo.create_reference('refs/locks/{}'.format(id), emptyblob)
        yield
        ref.delete()

    def locked(self, id):
        try:
            self.repo.lookup_reference('refs/locks/{}'.format(id))
        except KeyError:
            return False
        return True

    def sync_repo_index(self, checkout=True):
        """
        Updates the git repository's index with the current workspace index.
        If ``checkout`` is ``True``, the filesystem will be updated with the
        contents of the index.

        This is useful if you want to utilize the git repository using standard
        git tools.

        This function acquires a workspace-level INDEX lock.
        """
        with self.lock('INDEX'):
            self.repo.index.read_tree(self.index.oid)
            if checkout:
                self.repo.checkout()


class Branch(object):
    """
    A representation of a git branch that provides quick access to the ref,
    commit, and commit tree.
    """
    def __init__(self, repo, ref_name):
        try:
            self.ref = repo.lookup_reference(ref_name)
        except KeyError:
            msg = "Reference not found: {}".format(ref_name)
            raise exceptions.RepositoryError(msg)
        self.commit = self.ref.get_object()
        self.oid = self.commit.oid
        self.tree = self.commit.tree

    def __getitem__(self, path):
        return self.tree[path]
