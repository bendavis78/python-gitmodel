from gitmodel.models import GitModel
from gitmodel import fields

class Author(GitModel):
    email = fields.CharField()
    first_name = fields.CharField()
    last_name = fields.CharField()

class Post(GitModel):
    slug = fields.SlugField(id=True)
    title = fields.CharField()
    body = fields.CharField()
    author = fields.ToOneField(Author, required=False)
    image = fields.ImageField(required=False)
