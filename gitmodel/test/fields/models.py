from gitmodel import fields

# Since our workspace is instantiated inside the test, we need to wrap our model
# defintions inside a function

def setup(workspace):
    class Person(workspace.GitModel):
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

    class Author(workspace.GitModel):
        first_name = fields.CharField()
        last_name = fields.CharField()
        email = fields.CharField()
        language = fields.CharField(default='en-US')

    class Post(workspace.GitModel):
        author = fields.RelatedField(Author)
        slug = fields.SlugField(id=True)
        title = fields.CharField()
        body = fields.CharField()
        image = fields.BlobField(required=False)

    class User(Person):
        password = fields.CharField()
        last_login = fields.DateTimeField(required=False)
        last_read = fields.RelatedField(Post, required=False)

    # return a mock-module
    return type('models', (), {
        'Person': Person,
        'Author': Author,
        'Post': Post,
        'User': User
    })
