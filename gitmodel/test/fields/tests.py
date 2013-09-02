import os

import pygit2

from gitmodel.test import GitModelTestCase


class TestInstancesMixin(object):
    def setUp(self):
        super(TestInstancesMixin, self).setUp()

        from gitmodel.test.fields import models
        self.models = self.workspace.import_models(models)

        self.person = self.models.Person(
            slug='john-doe',
            first_name='John',
            last_name='Doe',
            email='jdoe@example.com',
        )

        self.author = self.models.Author(
            email='jdoe@example.com',
            first_name='John',
            last_name='Doe',
        )

        self.post = self.models.Post(
            slug='test-post',
            title='Test Post',
            body='Lorem ipsum dolor sit amet',
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
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_slug(self):
        self.person.slug = 'Foo Bar'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_integer(self):
        self.person.age = 20.5
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()
        self.person.age = 'twenty-one'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_float(self):
        self.person.tax_rate = '5%'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()
        self.person.tax_rate = '1.2.3'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_decimal(self):
        self.person.account_balance = 'one.two'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()
        self.person.account_balance = '1.2.3'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_date(self):
        # valid iso-8601 date
        self.person.birth_date = '1978-12-07'
        self.person.save()
        # not a valid iso-8601 date
        self.person.birth_date = '12/7/1978'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_datetime(self):
        # not a valid iso-8601 datetime
        self.person.date_joined = '12/8/2012 4:53pm'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()

    def test_validate_time(self):
        self.person.wake_up_call = '9am'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()
        self.person.wake_up_call = '2012-08-10 09:00'
        with self.assertRaises(self.exceptions.ValidationError):
            self.person.save()


class FieldTypeCheckingTest(TestInstancesMixin, GitModelTestCase):

    def assertTypesMatch(self, field, test_values, type):
        for value, eq_value in test_values.iteritems():
            setattr(self.person, field, value)
            self.person.save()
            person = self.models.Person.get(self.person.id)
            self.assertIsInstance(getattr(person, field), type)
            self.assertEqual(getattr(person, field), eq_value)

    def test_char(self):
        from datetime import datetime
        test_values = {
            'John': 'John',
            .007: '0.007',
            datetime(2012, 12, 12): '2012-12-12 00:00:00'
        }
        self.assertTypesMatch('first_name', test_values, basestring)

    def test_integer(self):
        test_values = {33: 33, '33': 33}
        self.assertTypesMatch('age', test_values, int)

    def test_float(self):
        test_values = {.825: .825, '0.825': .825}
        self.assertTypesMatch('tax_rate', test_values, float)

    def test_decimal(self):
        from decimal import Decimal
        test_values = {
            '1.23': Decimal('1.23'),
            '12.300': Decimal('12.3'),
            1: Decimal('1.0')
        }
        self.assertTypesMatch('account_balance', test_values, Decimal)

    def test_boolean(self):
        test_values = {
            True: True,
            False: False,
            1: True,
            0: False,
            None: False
        }
        self.assertTypesMatch('active', test_values, bool)

    def test_date(self):
        from datetime import date
        test_values = {
            '1978-12-7': date(1978, 12, 7),
            '1850-05-05': date(1850, 5, 5),
        }
        self.assertTypesMatch('birth_date', test_values, date)

    def test_datetime(self):
        from datetime import datetime
        from dateutil import tz
        utc = tz.tzutc()
        utc_offset = tz.tzoffset(None, -1 * 4 * 60 * 60)
        test_values = {
            '2012-05-30 14:32': datetime(2012, 5, 30, 14, 32),
            '1820-8-13 9:23:48Z': datetime(1820, 8, 13, 9, 23, 48, 0, utc),
            '2001-9-11 8:46:00-0400': datetime(2001, 9, 11, 8, 46, 0, 0,
                                               utc_offset),
            '2012-05-05 14:32:02.012345': datetime(2012, 5, 5, 14, 32, 2,
                                                   12345),
        }
        self.assertTypesMatch('date_joined', test_values, datetime)
        # test a normal date
        self.person.date_joined = '2012-01-01'
        self.person.save()
        person = self.models.Person.get(self.person.id)
        self.assertEqual(type(person.date_joined), datetime)
        self.assertEqual(person.date_joined, datetime(2012, 1, 1, 0, 0))

    def test_time(self):
        from datetime import time
        from dateutil import tz
        utc = tz.tzutc()
        utc_offset = tz.tzoffset(None, -1 * 4 * 60 * 60)
        test_values = {
            '14:32': time(14, 32),
            '9:23:48Z': time(9, 23, 48, 0, utc),
            '8:46:00-0400': time(8, 46, 0, 0, utc_offset)
        }
        self.assertTypesMatch('wake_up_call', test_values, time)


class RelatedFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_related(self):
        self.author.save()
        self.post.author = self.author
        self.post.save()
        post_id = self.post.get_id()
        post = self.models.Post.get(post_id)
        self.assertTrue(post.author.get_id() == self.author.get_id())


class BlobFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_blob_field(self):
        fd = open(os.path.join(os.path.dirname(__file__),
                               'git-logo-2color.png'))
        self.author.save()
        self.post.author = self.author
        self.post.image = fd
        self.post.save()

        #make sure stored file and original file are identical
        post = self.models.Post.get(self.post.get_id())
        saved_content = post.image.read()
        fd.seek(0)
        control = fd.read()
        self.assertEqual(saved_content, control,
                         "Saved blob does not match file")


class InheritedFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_inherited_local_fields(self):
        user = self.models.User(
            slug='john-doe',
            first_name='John',
            last_name='Doe',
            email='jdoe@example.com',
            password='secret'
        )
        user.save()
        # get user
        user_retreived = self.models.User.get(user.id)
        self.assertEqual(user_retreived.password, 'secret')

    def test_inherited_related_fields(self):
        self.author.save()
        self.post.author = self.author
        self.post.save()
        user = self.models.User(
            slug='john-doe',
            first_name='John',
            last_name='Doe',
            email='jdoe@example.com',
            password='secret',
            last_read=self.post
        )
        user.save()
        # get user
        user_retreived = self.models.User.get(user.id)
        self.assertEqual(user_retreived.last_read.get_id(), self.post.get_id())


class JSONFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_json_field(self):
        metadata = {
            'foo': 'bar',
            'baz': 'qux'
        }
        self.author.save()
        self.post.author = self.author
        self.post.metadata = metadata
        self.post.save()
        post = self.models.Post.get(self.post.slug)
        self.assertIsInstance(post.metadata, dict)
        self.assertDictEqual(post.metadata, metadata)


class GitObjectFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_gitobject_field(self):
        repo = self.workspace.repo
        test_commit = self.person.save(commit=True, message='Test Commit')
        test_blob = repo[self.workspace.index[self.person.get_data_path()].oid]
        test_tree = repo[test_commit].tree

        obj = self.models.GitObjectTestModel(
            blob=test_blob.oid,
            commit=test_commit,
            tree=test_tree.oid
        )
        obj.save()

        self.assertIsInstance(obj.commit, pygit2.Commit)
        self.assertEqual(obj.commit.oid, repo[test_commit].oid)
        self.assertIsInstance(obj.blob, pygit2.Blob)
        self.assertEqual(obj.blob.oid, test_blob.oid)
        self.assertIsInstance(obj.tree, pygit2.Tree)
        self.assertEqual(obj.tree.oid, test_tree.oid)

        err = '"commit" must be a valid git OID'
        with self.assertRaisesRegexp(self.exceptions.ValidationError, err):
            obj.commit = 'foo'
            obj.save()

        err = '"commit" must point to a Commit'
        with self.assertRaisesRegexp(self.exceptions.ValidationError, err):
            obj.commit = test_tree.oid
            obj.save()


class EmailFieldTest(TestInstancesMixin, GitModelTestCase):
    def test_email_field(self):
        invalid = '"email" must be a valid e-mail address'

        with self.assertRaisesRegexp(self.exceptions.ValidationError, invalid):
            self.author.email = 'jdoe[at]example.com'
            self.author.save()

        self.author.email = 'jdoe@example.com'
        self.author.save()
        id = self.author.id

        author = self.models.Author.get(id)
        self.assertEqual(author.email, 'jdoe@example.com')
