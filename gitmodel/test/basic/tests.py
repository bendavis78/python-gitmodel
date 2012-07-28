import os
import shutil
import unittest
import tempfile
import pygit2

class GitModelBasicTest(unittest.TestCase):
    def setUp(self):
        from gitmodel.test.basic import models
        from gitmodel import config
        from gitmodel.utils import json
        from gitmodel import exceptions

        self.models = models
        self.config = config
        self.json = json
        self.exceptions = exceptions

        config.REPOSITORY_PATH = tempfile.mkdtemp()

        # gitmodel does not create your repo for you
        self.repo = pygit2.init_repository(config.REPOSITORY_PATH)
        self.index = self.repo.index
        self.index.read()

        self.author = models.Author(
            email='jdoe@example.com',
            first_name='John',
            last_name='Doe'
        )

        self.post = models.Post(
            slug='test-post',
            title='Test Post',
            body='Lorem ipsum dolor sit amet',
        )

    def tearDown(self):
        # clean up test repo
        shutil.rmtree(self.config.REPOSITORY_PATH)

    def test_tree_name(self):
        self.assertEqual(self.models.Author._meta.tree_name, 'author')
        self.assertEqual(self.models.Post._meta.tree_name, 'post')

    def test_get_path(self):
        self.author.save()
        # author id should be 1
        path = self.author.get_path()
        self.assertEqual(path, 'author/1')

    def test_get_oid(self):
        self.author.save()
        test_oid = self.author.get_oid()
        oid = self.index[self.author.get_path()]
        self.assertEqual(oid, test_oid)

    def test_save(self):
        # Save is analagous to "git add"
        self.author.save()

        # get json using libgit2
        path = os.path.join(self.author._meta.tree_name, self.author.id)
        entry = self.index[path]
        blob = self.repo[entry.oid]

        # verify data
        data = self.json.loads(blob.data)
        self.assertEqual(data, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'jdoe@example.com'
        })

    def test_get_simple_object(self):
        self.author.save()
        author = self.models.Author.find(1)
        self.assertEqual(author.first_name, 'John')
        self.assertEqual(author.last_name, 'Doe')
        self.assertEqual(author.email, 'johndoe')

    def test_custom_id_field(self):
        # id should resolve to the slug field, since slug is marked as id=True
        self.post.save()
        self.assertEqual(self.post.id, self.post.slug)
    
    def test_id_auto_increment(self):
        author1 = self.author.save()
        author2 = self.models.Author(
            email='jane@example.com',
            first_name='Jane',
            last_name='Doe'
        )
        author2.save()

        self.assertEqual(author1.id, 1)
        self.assertEqual(author2.id, 2)

    def test_id_validator(self):
        # "/" and "\0" are both invalid characters
        with self.assertRaises(ValueError):
            self.author.email='foo/bar'
        with self.assertRaises(ValueError):
            self.author.email='foo\000bar'

    def test_create_object_with_binary(self):
        fd = open(os.path.join(self.static_dir, 'git-logo-2color.png'))
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

    def test_related(self):
        self.author.save()
        self.post.author = self.author
        self.post.save()
        self.assertUnless(False)

