from gitmodel import fields
from gitmodel.models import GitModel


class Author(GitModel):
    first_name = fields.CharField()
    last_name = fields.CharField()
    email = fields.CharField()
    language = fields.CharField(default='en-US')


class Post(GitModel):
    slug = fields.SlugField(id=True)
    title = fields.CharField()
    body = fields.CharField()
    image = fields.BlobField(required=False)


class Person(GitModel):
    first_name = fields.CharField()
    last_name = fields.CharField()
    email = fields.EmailField()


class User(Person):
    password = fields.CharField()
    date_joined = fields.DateField()


def get_path_custom(opts, object_id):
    import os
    # kinda silly, but good for testing that the opts object works
    model_name = opts.model_name.lower()
    model_name = model_name.replace('alternate', '-alt')
    return os.path.join(model_name, unicode(object_id), 'data.json')


class PostAlternate(GitModel):
    slug = fields.SlugField()
    title = fields.CharField()

    class Meta:
        id_field = 'slug'
        get_repo_path = get_path_custom
