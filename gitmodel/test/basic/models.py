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
    author = fields.ToOneField(Author, blank=True, null=True)
    image = fields.FileField(blank=True)
