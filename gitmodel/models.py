import os
from bisect import bisect
from contextlib import contextmanager
from gitmodel.serializers import serialize, deserialize
from gitmodel import exceptions
from gitmodel import conf
from gitmodel import fields
from gitmodel.utils import git

# attributes that can be overridden in a model's options ("Meta" class)
META_OPTS = ('git_tree_name', 'id_field')

class GitModelOptions(object):
    """
    An options class for ``GitModel``.
    """
    def __init__(self, meta, config):
        self.meta = meta
        self.config = config
        self.local_fields = []
        self.local_many_to_many = []
        self.git_tree_name = ''
        self.model_name = None
        self.parents = []
        self.id_field = None

    def contribute_to_class(self, cls, name):
        cls._meta = self

        # Default values for these options
        self.model_name = cls.__name__
        self.git_tree_name = self.model_name.lower()

        # Apply overrides from Meta
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            # Ignore private attributes
            for name in self.meta.__dict:
                if name.startswith('_'):
                    del meta_attrs[name]

            for attr_name in META_OPTS:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))


        del self.meta

    def add_field(self, field):
        """ Insert a field into the fields list in correct order """
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
        msg = "Field not '{}' not found on model '{}'".format(name, self.model_name)
        raise exceptions.FieldError(msg)

    def _fill_fields_cache(self):
        """
        Caches all fields, including fields from parents.
        """
        cache = []
        for parent in self.parents:
            for field in parent._meta.fields:
                # only add id field if not specified locally
                if not (field.id and any(f.id for f in self.local_fields)):
                    cache.append(field)
        cache.extend(self.local_fields)
        self._field_cache = tuple(cache)

    def _prepare(self, model):
        # set up id field
        if self.id_field is None:
            declared_id_fields = [f for f in self.fields if f.id]
            if len(declared_id_fields) > 1:
                import ipdb; ipdb.set_trace()
                raise exceptions.ConfigurationError("You may only have one id field per model")
            elif len(declared_id_fields) == 1:
                self.id_field = declared_id_fields[0].name
            else:
                # add an automatic uuid field
                auto = fields.UUIDField(id=True, autocreated=True)
                # add to the beginning of the fields list
                auto.creation_counter = -1
                model.add_to_class('id', auto)
                self.id_field = 'id'


class DeclarativeMetaclass(type):
    def __new__(cls, name, bases, attrs):
        parents = [b for b in bases if isinstance(b, DeclarativeMetaclass)]
        # Similate MRO
        parents.reverse()

        # Create the class, while leaving out the declared attributes
        module = attrs.pop('__module__')
        new_class = super(DeclarativeMetaclass, cls).__new__(cls, name, bases, 
                {'__module__': module})

        config = attrs.pop('__config__', None)
        
        # grab the declared Meta
        meta = attrs.pop('Meta', None)
        if not meta:
            # if not declared, make sure we use parent's meta
            meta = getattr(new_class, 'Meta', None)

        if config is None:
            config = parents[0]._meta.config

        # Add _meta to the new class. The _meta property is an instance of 
        # GitModelOptions, based off of the optionall declared "Meta" class
        new_class.add_to_class('_meta', GitModelOptions(meta, config))

        # Add all attributes to the class

        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        local_field_names = [f.name for f in new_class._meta.local_fields]

        # Handle parents
        for base in parents:
            if not hasattr(base, '_meta'):
                # Ignore parents that have no _meta
                continue

            parent_fields = base._meta.local_fields

            # Check for duplicate field definitions in parents
            for field in parent_fields:
                if field.autocreated:
                    # skip adding autocreated fields to child class
                    continue
                if field.name in local_field_names:
                    msg = 'Duplicate field name "%s" in %r already exists in '\
                          'base model %r'
                    raise exceptions.FieldError(msg % (field.name, name, base.__name__))

            new_class._meta.parents.append(base)

        new_class._prepare()
        return new_class

    def _prepare(cls):
        """
        Prepares the class once cls._meta has been populated.
        """
        opts = cls._meta
        opts._prepare(cls)
        
        # Give the class a docstring
        if cls.__doc__ is None:
            cls.__doc__ = "{}({})".format(cls.__name__, ', '.join(f.name for f in opts.fields))
    
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

class GitModel(object):
    __metaclass__ = DeclarativeMetaclass
    __config__ = conf.global_settings

    def __init__(self, **kwargs):
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
            # only set attributes for properties that already exist on the class
            for prop in kwargs.keys():
                try:
                    if isinstance(getattr(self.__class__, prop), property):
                        setattr(self, prop, kwargs.pop(prop))
                except AttributeError:
                    pass
            if kwargs:
                raise TypeError("'{}' is an invalid keyword argument for this function".format(kwargs.keys()[0]))

        self.repo = git.Repository(self._meta.config)
        
        # set the initial branch to use
        self.branch = self._meta.config.DEFAULT_BRANCH

        super(GitModel, self).__init__()

    def save(self, ref=None, stage=False, commit=False, commit_info=None):
        # make sure model has clean data
        self.full_clean()

        format = self._meta.config.DEFAULT_SERIALIZER
        serialized = serialize(self, format)

        # create the entry
        blob = self.repo.create_blob(serialized)
        path, name = os.path.split(self.get_path())
        entry = (name, blob, git.GIT_MODE_NORMAL)

        ref = ref or self._meta.config.DEFAULT_BRANCH

        # get the current tree
        try:
            ref = self.repo.lookup_reference(ref)
        except KeyError:
            current_tree = None
        else:
            current_tree = self.repo[ref.oid].tree.oid

        # build the tree for this commit/stage
        tree_id = self.repo.build_path(path, (entry,), current_tree)

        
        # if commit and stage are both true, we don't need to stage
        if commit:
            commit_info = commit_info or {}
            return self.repo.create_commit(ref, tree_id, **commit_info)
        elif stage:
            self.repo.index.read_tree(tree_id)
            self.repo.index.write()
            return self.repo.index

        # leave it up to caller to decide what to do
        return tree_id

    def get_id(self):
        return getattr(self, self._meta.id_field)

    def get_path(self):
        return os.path.join(self._meta.git_tree_name, unicode(self.get_id()))

    def get_oid(self):
        tree = self.repo.get_tree(self.branch)
        try:
            return tree[self.get_path()].oid
        except KeyError:
            return None

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
            raw_value = getattr(self, field.name)
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
        with self.repo.lock(self.get_id()):
            yield
    
    @classmethod
    def get(cls, id, ref=None):
        """
        Gets the object associated with the given id
        """
        repo = git.Repository(cls._meta.config)
        if not ref:
            ref = cls._meta.config.DEFAULT_BRANCH
        head_oid = repo.lookup_reference(ref).oid
        tree = repo[head_oid].tree
        path = os.path.join(cls._meta.git_tree_name, unicode(id))
        try:
            blob = tree[path].oid
        except KeyError:
            name = cls.__name__
            raise exceptions.DoesNotExist("{} with id {} does not exist.".format(name, id))
        data = repo[blob].data
        format = cls._meta.config.DEFAULT_SERIALIZER
        return deserialize(cls, data, format)


class GitTreeModel(GitModel):
    """
    A GitModel which is stored using a git tree structure.
    """
    pass
