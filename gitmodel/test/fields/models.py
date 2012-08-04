from gitmodel import models

class Person(models.GitModel):
    first_name = models.CharField()
    last_name = models.CharField()
    email = models.EmailField()
    age = models.IntegerField(null=True)
    account_balance = models.DecimalField(null=True)
    active = models.BooleanField(null=True)
