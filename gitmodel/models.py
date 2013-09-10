import os
from bisect import bisect
from contextlib import contextmanager
from importlib import import_module

import decorator

from gitmodel import exceptions
from gitmodel import fields
from gitmodel import utils


class GitModelOptions(object):
    """
    An options class for ``GitModel``.
    """
    # attributes that can be overridden in a model's options ("Meta" class)
    meta_opts = ('abstract', 'data_filename', 'get_data_path', 'id_attr')

    # reserved attributes
    reserved = ('oid',)

    def __init__(self, meta, workspace):
        self.meta = meta
        self.workspace = workspace
        self.abstract = False
        self.local_fields = []
        self.local_many_to_many = []
        self.model_name = None
        self.parents = []
        self.id_attr = None
        self.data_filename = 'data.json'
        self._serializer = None

    @property
    def serializer(self):
        if self._serializer is None:
            from gitmodel.conf import defaults
            default_serializer = defaults.DEFAULT_SERIALIZER
            if self.workspace is not None:
                default_serializer = self.workspace.config.DEFAULT_SERIALIZER
            self._serializer = import_module(default_serializer)
        return self._serializer

    def contribute_to_class(self, cls, name):
        cls._meta = self

        # Default values for these options
        self.model_name = cls.__name__

        # Apply overrides from Meta
        if self.meta:
            # Ignore private attributes
            for name in dir(self.meta):
                if name.startswith('_') or name not in self.meta_opts:
                    continue

                value = getattr(self.meta, name)
                # if attr is a function, bind it to this instance
                if not isinstance(value, type) and hasattr(value, '__call__'):
                    value = value.__get__(self)
                setattr(self, name, value)

        self._declared_meta = self.meta
        del self.meta

    def get_data_path(self, object_id):
        """
        Default method for building the path name for a given id.

        This is used by a model instance's get_data_path() method, which simply
        passes the instance id.
        """
        model_name = self.model_name.lower()
        return os.path.join(model_name, unicode(object_id), self.data_filename)

    def add_field(self, field):
        """ Insert a field into the fields list in correct order """
        if field.name in self.reserved:
            raise exceptions.FieldError("{} is a reserved name and cannot be"
                                        "used as a field name.")
        # bisect calls field.__cmp__ which uses field.creation_counter to
        # maintain the correct order
        position = bisect(self.local_fields, field)
        self.local_fields.insert(position, field)

        # invalidate the field cache
        if hasattr(self, '_field_cache'):
            del self._field_cache

    @property
    def fields(self):
        """
        Returns a list of field objects available for this model (including
        through parent models).

        Callers are not permitted to modify this list, since it's a reference
        to this instance (not a copy)
        """
        # get cached field names. if not cached, then fill the cache.
        if not hasattr(self, '_field_cache'):
            self._fill_fields_cache()
        return self._field_cache

    def get_field(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        msg = "Field not '{}' not found on model '{}'"
        raise exceptions.FieldError(msg.format(name, self.model_name))

    def _fill_fields_cache(self):
        """
        Caches all fields, including fields from parents.
        """
        cache = []
        has_id_attr = self.id_attr or any(f.id for f in self.local_fields)
        for parent in self.parents:
            for field in parent._meta.fields:
                # skip if overridden locally
                if field.name in (f.name for f in self.local_fields):
                    continue
                # only add id field if not specified locally
                if field.id and has_id_attr:
                    continue
                cache.append(field)
        cache.extend(self.local_fields)
        self._field_cache = tuple(cache)

    def _prepare(self, model):
        # set up id field
        if self.id_attr is None:
            declared_id_fields = [f for f in self.fields if f.id]
            if len(declared_id_fields) > 1:
                msg = "You may only have one id field per model"
                raise exceptions.ConfigurationError(msg)
            elif len(declared_id_fields) == 1:
                self.id_attr = declared_id_fields[0].name
            else:
                # add an automatic uuid field
                auto = fields.UUIDField(id=True, autocreated=True)
                # add to the beginning of the fields list
                auto.creation_counter = -1
                model.add_to_class('id', auto)
                self.id_attr = 'id'


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        super_new = super(DeclarativeMetaclass, cls).__new__

        parents = [b for b in bases if isinstance(b, DeclarativeMetaclass)]
        parents.reverse()

        if not parents:
            # Don't do anything special for the base GitModel
            return super_new(cls, name, bases, attrs)

        # workspace that will be passed to GitModelOptions
        workspace = attrs.pop('__workspace__', None)

        # inherit parent workspace if not provided
        if not workspace:
            if len(parents) > 0 and hasattr(parents[0], '_meta'):
                workspace = parents[0]._meta.workspace

        # don't do anything special for GitModels without a workspace
        if not workspace:
            return super_new(cls, name, bases, attrs)

        # Create the new class, while leaving out the declared attributes
        # which will be added later
        module = attrs.pop('__module__')
        options_cls = attrs.pop('__optclass__', None)
        new_class = super_new(cls, name, bases, {'__module__': module})

        # grab the declared Meta
        meta = attrs.pop('Meta', None)
        base_meta = None
        if parents and hasattr(parents[0], '_meta'):
            base_meta = parents[0]._meta

        # Add _meta to the new class. The _meta property is an instance of
        # GitModelOptions, based off of the optional declared "Meta" class
        if options_cls is None:
            if base_meta:
                options_cls = type(base_meta)
            else:
                options_cls = GitModelOptions

        if meta is None:
            # if meta is not declared, use the closest parent's meta
            meta = next((p._meta._declared_meta for p in parents if
                        hasattr(p, '_meta') and p._meta._declared_meta), None)
            # don't inherit the abstract property
            if hasattr(meta, 'abstract'):
                meta.abstract = False

        opts = options_cls(meta, workspace)

        new_class.add_to_class('_meta', opts)

        # Add all attributes to the class
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        # Handle parents
        for parent in parents:
            if not hasattr(parent, '_meta'):
                # Ignore parents that have no _meta
                continue
            new_class._check_parent_fields(parent)
            new_class._meta.parents.append(parent)

        new_class._prepare()

        # make sure the model is registered in its workspace
        workspace.register_model(new_class)

        return new_class

    def _check_parent_fields(cls, parent, child=None):
        """
        Checks a parent class's inheritance chain for field conflicts
        """
        if child is None:
            child = cls

        local_field_names = [f.name for f in child._meta.local_fields]
        # Check for duplicate field definitions in parent
        for field in parent._meta.local_fields:
            if not field.autocreated and field.name in local_field_names:
                msg = ('Duplicate field name "{0}" in {1!r} already exists in '
                       'parent model {2!r}')
                msg = msg.format(field.name, child.__name__, parent.__name__)
                raise exceptions.FieldError(msg)

        # check base's inheritance chain
        for p in parent._meta.parents:
            parent._check_parent_fields(p, child)

    def _prepare(cls):
        """
        Prepares the class once cls._meta has been populated.
        """
        opts = cls._meta
        opts._prepare(cls)

        # Give the class a docstring
        if cls.__doc__ is None:
            fields = ', '.join(f.name for f in opts.fields)
            cls.__doc__ = "{}({})".format(cls.__name__, fields)

    def add_to_class(cls, name, value):
        """
        If the given value defines a ``contribute_to_class`` method, that will
        be called. Otherwise, this is an alias to setattr.  This allows objects
        to have control over how they're added to a class during its creation.
        """
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)


@decorator.decorator
def concrete(func, self, *args, **kwargs):
    """
    Causes a model's method to require a non-abstract, workspace-bound model.
    """
    # decorator should work for classmethods as well as instance methods
    model = self
    if not isinstance(model, type):
        model = type(self)
    if not hasattr(model, '_meta'):
        msg = ("Cannot call {0.__name__}.{1.__name__}() because {0!r} "
               "has not been registered with a workspace")
        raise exceptions.GitModelError(msg.format(model, func))
    if model._meta.abstract:
        msg = "Cannot call {1.__name__}() on abstract model {0.__name__} "
        raise exceptions.GitModelError(msg.format(model, func))
    return func(self, *args, **kwargs)


class GitModel(object):
    __metaclass__ = DeclarativeMetaclass
    __workspace__ = None

    @concrete
    def __init__(self, **kwargs):
        """
        Create an instance of a GitModel.

        Field name/value pairs may be provided as kwargs to set the initial
        value for those fields. If "oid" is provided in kwargs, it is assumed
        that this model is being instantiated from an existing instance in the
        git repository. Deserializing a model will automatically set this oid.
        """
        self._oid = kwargs.pop('oid', None)

        # To keep things simple, we only accept attribute values as kwargs
        # Check for fields in kwargs
        for field in self._meta.fields:
            # if a field value was given in kwargs, get its value, otherwise,
            # get the field's default value
            if kwargs:
                try:
                    val = kwargs.pop(field.name)
                except KeyError:
                    val = field.default
            else:
                val = field.default
            setattr(self, field.name, val)

        # Handle any remaining keyword arguments
        if kwargs:
            # only set attrs for properties that already exist on the class
            for prop in kwargs.keys():
                try:
                    if isinstance(getattr(type(self), prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                msg = "'{0}' is an invalid keyword argument for this function"
                raise TypeError(msg.format(kwargs.keys()[0]))

        super(GitModel, self).__init__()

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = '[Bad Unicode Data]'
        return u'<{0}: {1}>'.format(self._meta.model_name, u)

    def __str__(self):
        if hasattr(self, '__unicode__'):
            return unicode(self).encode('utf-8')
        return '{0} object'.format(self._meta.model_name)

    def save(self, commit=False, **commit_info):
        # make sure model has clean data
        self.full_clean()

        # if this is new, make sure we don't overwrite an existing instance by
        # accident
        if not self.oid:
            id = self.get_id()
            try:
                type(self).get(id)
            except exceptions.DoesNotExist:
                pass
            else:
                err = 'A {} instance already exists with id "{}"'.format(
                    type(self).__name__, self.get_id())
                raise exceptions.IntegrityError(err)

        serialized = self._meta.serializer.serialize(self)

        workspace = self._meta.workspace

        # only allow commit-during-save if workspace doesn't have pending
        # changes.
        if commit and workspace.has_changes():
            msg = "Repository has pending changes. Cannot save-commit until "\
                  "pending changes have been comitted."
            raise exceptions.RepositoryError(msg)

        # create the git object and set the instance oid
        self._oid = workspace.add_blob(self.get_data_path(), serialized)

        # go through fields that have their own save handler
        for field in self._meta.fields:
            value = getattr(self, field.name)
            field.post_save(value, self, commit)

        # if our path has changed, remove the old path. This generally only
        # happens with a custom mutable id_attr.
        old_path = getattr(self, '_current_path', None)
        new_path = self.get_data_path()
        if old_path and old_path != new_path:
            rmpath = os.path.dirname(old_path)
            self._meta.workspace.remove(rmpath)

        self._current_path = self.get_data_path()

        if commit:
            return workspace.commit(**commit_info)

    def get_id(self):
        return getattr(self, self._meta.id_attr)

    def get_data_path(self):
        id = unicode(self.get_id())
        return self._meta.get_data_path(id)

    @property
    def oid(self):
        """
        The OID of the git blob used to store this object. This is a read-only
        property.
        """
        return self._oid

    def clean(self):
        """
        Hook for doing any extra model-secific validation after fields have
        been cleaned.
        """
        pass

    def clean_fields(self):
        """
        Validates all fields on the model.
        """
        for field in self._meta.fields:
            raw_value = field.get_raw_value(self)
            setattr(self, field.name, field.clean(raw_value, self))

    def full_clean(self):
        """
        Calls clean_fields() and clean()
        """
        self.clean_fields()
        self.clean()

    @contextmanager
    def lock(self):
        """
        Acquires a lock for this object.
        """
        with self._meta.workspace.lock(self.get_id()):
            yield

    @classmethod
    @concrete
    def get(cls, id, treeish=None):
        """
        Gets the object associated with the given id
        """
        workspace = cls._meta.workspace
        path = cls._meta.get_data_path(id)

        if treeish:
            tree = utils.treeish_to_tree(workspace.repo, treeish)
        else:
            tree = workspace.index

        msg = "{} with id {}{} does not exist."
        name = cls._meta.model_name
        revname = treeish and '@{}'.format(treeish) or ''
        msg = msg.format(name, id, revname)

        if not tree:
            raise exceptions.DoesNotExist(msg)

        try:
            blob = tree[path].oid
        except KeyError:
            raise exceptions.DoesNotExist(msg)
        data = workspace.repo[blob].data

        return cls._meta.serializer.deserialize(workspace, data, blob)

    @classmethod
    @concrete
    def all(cls):
        """
        Returns a generator for all instances of this model.
        """
        pattern = cls._meta.get_data_path('*')
        workspace = cls._meta.workspace
        repo = workspace.repo

        def all():
            for path in utils.path.glob(repo, workspace.index, pattern):
                blob = workspace.index[path].oid
                data = workspace.repo[blob].data
                yield cls._meta.serializer.deserialize(workspace, data, blob)

        return ModelSet(all())

    @classmethod
    @concrete
    def delete(cls, id, commit=False, **commit_info):
        """
        Removes an object from its parent tree. This is a recursive operation,
        so if the stored object contains other objects within its directory,
        they will be removed as well. This is not the default case, but may be
        if the model employs a custom method for generating its data path.
        """
        cls.get(id)
        path = os.path.dirname(cls._meta.get_data_path(id))
        cls._meta.workspace.remove(path)

        if commit:
            return cls._meta.workspace.commit(**commit_info)


class ModelSet(object):
    """
    A read-only container type initailized with a generator
    """
    def __init__(self, gen):
        self._gen = gen

    def __iter__(self):
        return self._gen

    def __getitem__(self, key):
        try:
            return next(o for i, o in enumerate(self._gen) if i == key)
        except StopIteration:
            raise IndexError("Index out of range")

    def __next__(self):
        return next(self._gen)

    def __contains__(self, item):
        return next(o for o in self._gen if o == item)
