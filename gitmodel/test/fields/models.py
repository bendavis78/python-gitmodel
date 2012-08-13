from gitmodel import fields

# Since our repo is instantiated inside the test, we need to wrap our model
# defintions inside a function

def setup(repo):
    class Person(repo.GitModel):
        slug = fields.SlugField()
        first_name = fields.CharField()
        last_name = fields.CharField()
        email = fields.EmailField()
        age = fields.IntegerField(required=False)
        account_balance = fields.DecimalField(required=False)
        birth_date = fields.DateField(required=False)
        date_joined = fields.DateTimeField(required=False)
        active = fields.BooleanField(required=False)
        tax_rate = fields.FloatField(required=False)
        wake_up_call = fields.TimeField(required=False)

    # return a mock-module
    return type('models', (), {
        'Person': Person,
    })
