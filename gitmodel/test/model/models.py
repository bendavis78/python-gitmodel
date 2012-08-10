from gitmodel import fields

# Since our repo is instantiated inside the test, we need to wrap our model
# defintions inside a function

def setup(repo):
    class Author(repo.GitModel):
        first_name = fields.CharField()
        last_name = fields.CharField()
        email = fields.CharField()
        language = fields.CharField(default='en-US')

    class Post(repo.GitModel):
        slug = fields.SlugField(id=True)
        title = fields.CharField()
        body = fields.CharField()
        author = fields.ToOneField(Author, blank=True, null=True)
        image = fields.FileField(blank=True)

    class Person(repo.GitModel):
        first_name = fields.CharField()
        last_name = fields.CharField()
        email = fields.EmailField()

    class User(Person):
        password = fields.CharField()
        date_joined = fields.DateField()
    
    # return a mock-module
    return type('models', (), {
        'Author': Author,
        'Post': Post,
        'Person': Person,
        'User': User
    })
