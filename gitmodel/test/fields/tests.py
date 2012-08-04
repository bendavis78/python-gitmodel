from gitmodel.test import GitModelTestCase

class TestInstancesMixin(object):
    def setUp(self):
        super(TestInstancesMixin, self).setup()

        from gitmodel.test.fields import models
        self.models = models

        # person object with valid fields, which we'll change to invalid in the
        # individual tests
        self.person = models.Person(
            slug = 'john-doe',
            first_name = 'John',
            last_name = 'Doe',
            email = 'jdoe@example.com',
            age = 21,
            account_balance = 123.45,
            active = True
        )

class FieldValidationTest(TestInstancesMixin, GitModelTestCase):
    def test_validate_not_empty(self):
        # empty string on required field should trigger validationerror
        self.person.last_name = ''
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()
        
        # None on required field should trigger validationerror
        self.person.last_name = None
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_email(self):
        self.person.email = 'foo_at_example.com'
        with self.assertRasies(self.exceptions.ValidationError):
            self.person.save()
    
    def test_validate_slug(self):
        self.slug = 'Foo Bar'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_integer(self):
        self.person.age = 'twenty-one'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_float(self):
        #TODO
        self.assertUnless(False)

    def test_validate_decimal(self):
        #TODO
        self.assertUnless(False)

    def test_validate_boolean(self):
        #TODO
        self.assertUnless(False)

    def test_validate_date(self):
        #TODO
        self.assertUnless(False)

    def test_validate_datetime(self):
        #TODO
        self.assertUnless(False)

    def test_validate_time(self):
        #TODO
        self.assertUnless(False)

    def test_validate_list(self):
        #TODO
        self.assertUnless(False)

    def test_validate_dict(self):
        #TODO
        self.assertUnless(False)

class FieldTypeCheckingTest(TestInstancesMixin, GitModelTestCase):
    def test_char(self):
        #TODO make sure char is typed correctly
        self.assertUnless(False)

    def test_integer(self):
        #TODO make sure integer is typed correctly
        self.assertUnless(False)
    
    def test_float(self):
        #TODO: make sure float is typed correctly
        #Note: ints should be typecasted to floats
        self.assertUnless(False)

    def test_decimal(self):
        #TODO: make sure decimal is typed correctly
        #Note: ints, floats should be typecasted to Decimal
        self.assertUnless(False)

    def test_boolean(self):
        #TODO: make sure boolean is typed correctly
        self.assertUnless(False)

    def test_date(self):
        #TODO: make sure date is typed correctly
        self.assertUnless(False)

    def test_datetime(self):
        #TODO: make sure datetime is typed correctly
        self.assertUnless(False)

    def test_time(self):
        #TODO: make sure time is typed correctly
        self.assertUnless(False)

    def test_list(self):
        #TODO: make sure lists are typed correctly
        self.assertUnless(False)

    def test_dict(self):
        #TODO: make sure dicts are typed correctly
        self.assertUnless(False)

class RelatedFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_related(self):
        self.author.save()
        self.post.author = self.author
        self.post.save()
        self.assertUnless(False)


class InheritedFieldTest(GitModelTestCase):
    def test_inherited_local_fields(self):
        #TODO:
        self.assertUnless(False)

    def test_inherited_related_fields(self):
        #TODO
        self.assertUnless(False)
