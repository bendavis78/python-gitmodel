from gitmodel import fields
from gitmodel import models


class Person(models.GitModel):
    slug = fields.SlugField()
    first_name = fields.CharField()
    last_name = fields.CharField()
    email = fields.EmailField()
    age = fields.IntegerField(required=False)
    account_balance = fields.DecimalField(required=False)
    birth_date = fields.DateField(required=False)
    active = fields.BooleanField(required=False)
    tax_rate = fields.FloatField(required=False)
    wake_up_call = fields.TimeField(required=False)
    date_joined = fields.DateTimeField(required=False)


class Author(models.GitModel):
    first_name = fields.CharField()
    last_name = fields.CharField()
    email = fields.CharField()
    language = fields.CharField(default='en-US')


class Post(models.GitModel):
    author = fields.RelatedField(Author)
    slug = fields.SlugField(id=True)
    title = fields.CharField()
    body = fields.CharField()
    image = fields.BlobField(required=False)


class User(Person):
    password = fields.CharField()
    last_login = fields.DateTimeField(required=False)
    last_read = fields.RelatedField(Post, required=False)
