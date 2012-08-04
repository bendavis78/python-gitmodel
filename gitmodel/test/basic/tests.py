import os
import json
from gitmodel.test import GitModelTestCase

class TestInstancesMixin(object):
    def setUp(self):
        super(TestInstancesMixin, self).setUp()
        
        from gitmodel.test.basic import models
        self.models = models
        
        self.author = models.Author(
            email='jdoe@example.com',
            first_name='John',
            last_name='Doe',
        )

        self.post = models.Post(
            slug='test-post',
            title='Test Post',
            body='Lorem ipsum dolor sit amet',
        )

class GitModelBasicTest(TestInstancesMixin, GitModelTestCase):

    def test_meta(self):
        self.assertIsNotNone(self.models.Author._meta)

    def test_config(self):
        from gitmodel.conf import Config
        self.assertIsInstance(self.models.Author._meta.config, Config)

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

    def test_property_assign(self):
        author = self.models.Author()
        author.first_name = 'John'
        self.assertEqual(author.first_name, 'John')

    def test_tree_name(self):
        self.assertEqual(self.models.Author._meta.git_tree_name, 'author')
        self.assertEqual(self.models.Post._meta.git_tree_name, 'post')

    def test_get_path(self):
        self.author.save()
        path = self.author.get_path()
        self.assertEqual(path, 'author/{}'.format(self.author.id))

    def test_get_oid(self):
        from gitmodel.utils import git
        self.author.save(commit=True)
        test_oid = self.author.get_oid()
        self.assertIsNotNone(test_oid)
        tree = self.author.repo.get_tree('refs/heads/master')
        obj = git.get_object_by_path(tree, self.author.get_path())
        self.assertEqual(obj.oid, test_oid)

    def test_field_default(self):
        self.assertEqual(self.author.language, 'en-US')

    def test_save(self):
        # save without adding to index or commit
        tree_id = self.author.save()
        tree = self.repo[tree_id]

        # get json from the returned tree using pygit2 code
        entry = tree[self.author.get_path()]
        blob = self.repo[entry.oid]

        # verify data
        data = json.loads(blob.data)
        self.assertItemsEqual(data, {
            'id': self.author.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'language': '',
        })

    def test_save_stage(self):
        index = self.author.save(stage=True)
        entry = index[self.author.get_path()]
        blob = self.repo[entry.oid]

        # verify data
        data = json.loads(blob.data)
        self.assertItemsEqual(data, {
            'id': self.author.id,
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
        commit_id = self.author.save(commit=True, commit_info=commit_info)
        commit = self.repo[commit_id]

        # verify commit
        self.assertEqual(commit.author.name, 'John Doe')
        self.assertEqual(commit.author.email, 'jdoe@example.com')
        self.assertEqual(commit.message, 'Testing save with commit')

        # get json from the returned tree using pygit2 code
        entry = commit.tree[self.author.get_path()]
        blob = self.repo[entry.oid]

        # verify data
        data = json.loads(blob.data)
        self.assertItemsEqual(data, {
            'id': self.author.id,
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com',
            'language': '',
        })

    def test_save_commit_history(self):
        self.assertTrue(False)

    def test_get_simple_object(self):
        self.author.save(commit=True)
        author = self.models.Author.get(self.author.id)
        self.assertEqual(author.first_name, 'John')
        self.assertEqual(author.last_name, 'Doe')
        self.assertEqual(author.email, 'jdoe@example.com')

    def test_id_validator(self):
        # "/" and "\0" are both invalid characters
        with self.assertRaises(ValueError):
            self.author.email='foo/bar'
        with self.assertRaises(ValueError):
            self.author.email='foo\000bar'

    def test_save_with_binary(self):
        fd = open(os.path.join(os.path.dirname(__file__), 'git-logo-2color.png'))
        self.post.image = fd
        self.post.save()

        #make sure stored file and original file are identical
        fd.seek(0)
        entry = self.repo[self.post.get_path()]
        blob = self.repo[entry.oid]
        orig_content = fd.read()
        self.assertEqual(blob, orig_content)

    def test_require_fields(self):
        test_author = self.models.Author(first_name='Jane')
        with self.assertRaises(self.exceptions.ValidationError):
            test_author.save()

    def test_custom_id_field(self):
        # id should resolve to the slug field, since slug is marked as id=True
        self.post.save()
        self.assertEqual(self.post.id, self.post.slug)
    
    def test_basic_inheritance(self):
        #TODO
        self.assertTrue(False)

    def test_inherited_field_clash(self):
        #TODO
        # implemented in metclass creation
        self.assertTrue(False)
