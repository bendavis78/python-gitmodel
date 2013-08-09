import os
import json
from gitmodel.test import GitModelTestCase


class TestInstancesMixin(object):
    def setUp(self):
        super(TestInstancesMixin, self).setUp()

        from gitmodel.test.model import models
        from gitmodel import exceptions
        from gitmodel import fields

        self.exceptions = exceptions
        self.fields = fields
        self.workspace.import_models(models)
        self.models = self.workspace.models

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


class GitModelBasicTest(TestInstancesMixin, GitModelTestCase):

    def test_type(self):
        author = self.models.Author()
        self.assertIsInstance(author, self.models.GitModel)

    def test_meta(self):
        self.assertIsNotNone(self.models.Author._meta)

    def test_workspace_in_model_meta(self):
        from gitmodel.workspace import Workspace
        self.assertIsInstance(self.models.Author._meta.workspace, Workspace)

    def test_fields_added_to_meta(self):
        fields = [f.name for f in self.models.Author._meta.fields]
        self.assertEqual(fields, [
            'id',
            'first_name',
            'last_name',
            'email',
            'language'
        ])

    def test_has_id_field(self):
        self.assertIsNotNone(self.author._meta.id_field)

    def test_id(self):
        self.assertTrue(hasattr(self.author, 'id'))

    def test_create_from_kwargs(self):
        self.assertEqual(self.author.first_name, 'John')

    def test_property_assignment(self):
        author = self.models.Author()
        author.first_name = 'John'
        self.assertEqual(author.first_name, 'John')

    def test_get_path(self):
        self.author.save()
        path = self.author.get_path()
        test_path = 'author/{}/data.json'.format(self.author.get_id())
        self.assertEqual(path, test_path)

    def test_get_oid(self):
        self.author.save(commit=True)
        test_oid = self.author.get_oid()
        self.assertIsNotNone(test_oid)
        obj = self.workspace.index[self.author.get_path()]
        self.assertEqual(obj.oid, test_oid)

    def test_field_default(self):
        self.assertEqual(self.author.language, 'en-US')

    def test_save(self):
        # save without adding to index or commit
        self.author.save()

        # get json from the returned tree using pygit2 code
        entry = self.workspace.index[self.author.get_path()]
        blob = self.workspace.repo[entry.oid]

        # verify data
        data = json.loads(blob.data)
        self.assertItemsEqual(data, {
            'id': self.author.get_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'language': '',
        })

    def test_save_commit(self):
        commit_info = {
            'author': ('John Doe', 'jdoe@example.com'),
            'message': 'Testing save with commit'
        }
        commit_id = self.author.save(commit=True, **commit_info)
        commit = self.workspace.repo[commit_id]

        # verify commit
        self.assertEqual(commit.author.name, 'John Doe')
        self.assertEqual(commit.author.email, 'jdoe@example.com')
        self.assertEqual(commit.message, 'Testing save with commit')

        # get json from the returned tree using pygit2 code
        entry = commit.tree[self.author.get_path()]
        blob = self.workspace.repo[entry.oid]

        # verify data
        data = json.loads(blob.data)
        self.assertItemsEqual(data, {
            'id': self.author.get_id(),
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'language': '',
        })

    def test_diff_nobranch(self):
        # Tests a diff when a save is made with no previous commits
        self.maxDiff = None
        self.author.save()
        self.assertTrue(self.workspace.has_changes())
        blob_hash = self.workspace.index[self.author.get_path()].hex[:7]
        diff = open(os.path.join(os.path.dirname(__file__),
                                 'diff_nobranch.diff')).read()
        diff = diff.format(self.author.get_path(), blob_hash, self.author.id)
        self.assertMultiLineEqual(diff, self.workspace.diff().patch)

    def test_diff_branch(self):
        # Tests a diff when a save is made with previous commits
        self.maxDiff = None
        self.author.save(commit=True, message="Test first commit")
        blob_hash_1 = self.workspace.index[self.author.get_path()].hex[:7]
        self.author.first_name = 'Jane'
        self.author.save()
        blob_hash_2 = self.workspace.index[self.author.get_path()].hex[:7]
        diff = open(os.path.join(os.path.dirname(__file__),
                                 'diff_branch.diff')).read()
        diff = diff.format(self.author.get_path(), blob_hash_1, blob_hash_2,
                           self.author.id)
        self.assertMultiLineEqual(diff, self.workspace.diff().patch)

    def test_save_commit_history(self):
        # Test that commited models save correctly
        import pygit2
        commit1 = self.author.save(commit=True, message="Test first commit")
        self.author.first_name = 'Jane'
        commit2 = self.author.save(commit=True, message="Changed name to Jane")
        self.assertEqual(self.workspace.branch.commit.oid, commit2)
        self.assertEqual(self.workspace.repo[commit2].parents[0].oid, commit1)
        walktree = self.workspace.repo.walk(self.workspace.branch.oid,
                                            pygit2.GIT_SORT_TIME)
        commits = [c for c in walktree]
        self.assertEqual(commits[0].oid, commit2)
        self.assertEqual(commits[1].oid, commit1)

    def test_get_simple_object(self):
        self.author.save(commit=True)
        author = self.models.Author.get(self.author.get_id())
        self.assertEqual(author.first_name, 'John')
        self.assertEqual(author.last_name, 'Doe')
        self.assertEqual(author.email, 'jdoe@example.com')

    def test_save_custom_id(self):
        self.post.save(commit=True)
        post = self.models.Post.get('test-post')
        self.assertEqual(post.get_id(), 'test-post')
        self.assertEqual(post.slug, 'test-post')
        self.assertEqual(post.title, 'Test Post')

    def test_id_validator(self):
        # "/" and "\0" are both invalid characters
        self.author.id = 'foo/bar'
        with self.assertRaises(self.exceptions.ValidationError):
            self.author.save()

        self.author.id = 'foo\000bar'
        with self.assertRaises(self.exceptions.ValidationError):
            self.author.save()

    def test_require_fields(self):
        test_author = self.models.Author(first_name='Jane')
        with self.assertRaises(self.exceptions.ValidationError):
            test_author.save()

    def test_custom_id_field(self):
        # id should resolve to the slug field, since slug is marked as id=True
        self.post.save()
        self.assertEqual(self.post.get_id(), self.post.slug)

    def test_basic_inheritance(self):
        fields = [f.name for f in self.models.User._meta.fields]
        self.assertEqual(fields, [
            'id',
            'first_name',
            'last_name',
            'email',
            'password',
            'date_joined',
        ])

    def test_inherited_field_clash(self):
        with self.assertRaises(self.exceptions.FieldError):
            # first_name should clash with the parent models' first_name field
            class User(self.models.Person):
                first_name = self.fields.CharField()
                password = self.fields.CharField()
                date_joined = self.fields.DateField()

    def test_meta_overrides(self):
        self.assertEqual(self.models.PostAlternate._meta.id_field, 'slug')

    def test_make_path_override(self):
        post = self.models.PostAlternate(slug='foobar', title='Foobar')
        post.save()
        self.assertEqual(post.get_path(), 'post-alt/foobar/data.json')

    def test_commit_when_pending_changes(self):
        self.author.save()
        self.author.first_name = 'Jane'
        with self.assertRaises(self.exceptions.RepositoryError):
            self.author.save(commit=True)

    def test_multiple_saves_before_commit(self):
        self.author.save()
        author_id = self.author.get_id()
        self.post.save()
        post_id = self.post.get_id()
        self.assertEqual(author_id, self.models.Author.get(author_id).get_id())
        self.assertEqual(post_id, self.models.Post.get(post_id).get_id())
