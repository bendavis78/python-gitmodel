import pygit2
from gitmodel.test import GitModelTestCase


class GitModelUtilsTest(GitModelTestCase):
    def setUp(self):
        super(GitModelUtilsTest, self).setUp()
        self.repo = self.workspace.repo

    def _get_test_tree(self):
        repo = self.repo
        # builds the following tree:
        #
        # foo/
        #   bar/
        #     baz/
        #       test2.txt
        #     test.txt
        #     test3.txt
        test_txt = repo.create_blob("TEST")
        test2_txt = repo.create_blob("TEST 2")
        test3_text = repo.create_blob("TEST 3")
        baz_tb = repo.TreeBuilder()
        baz_tb.insert('test2.txt', test2_txt, pygit2.GIT_FILEMODE_BLOB)
        baz = baz_tb.write()
        bar_tb = repo.TreeBuilder()
        bar_tb.insert('test.txt', test_txt, pygit2.GIT_FILEMODE_BLOB)
        bar_tb.insert('test3.txt', test3_text, pygit2.GIT_FILEMODE_BLOB)
        bar_tb.insert('baz', baz, pygit2.GIT_FILEMODE_TREE)
        bar = bar_tb.write()
        foo_tb = repo.TreeBuilder()
        foo_tb.insert('bar', bar, pygit2.GIT_FILEMODE_TREE)
        foo = foo_tb.write()
        root_tb = repo.TreeBuilder()
        root_tb.insert('foo', foo, pygit2.GIT_FILEMODE_TREE)
        root = root_tb.write()
        return root

    def test_describe_tree(self):
        from gitmodel import utils
        root = self._get_test_tree()
        desc = utils.path.describe_tree(self.repo, root)
        test_desc = ('foo/\n'
                     '  bar/\n'
                     '    baz/\n'
                     '      test2.txt\n'
                     '    test.txt\n'
                     '    test3.txt')
        self.assertMultiLineEqual(desc, test_desc)

    def test_make_signature(self):
        from gitmodel import utils
        from datetime import datetime
        from time import time
        from dateutil.tz import tzlocal

        # Get local offset
        timestamp = time()
        dt = datetime.fromtimestamp(timestamp)
        aware = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                         dt.second, dt.microsecond, tzinfo=tzlocal())
        seconds = aware.utcoffset().days * 86400
        seconds += aware.utcoffset().seconds
        offset = seconds / 60

        test_sig = utils.make_signature('Tester Test', 'test@example.com',
                                        timestamp=timestamp)
        self.assertEqual(test_sig.name, 'Tester Test')
        self.assertEqual(test_sig.email, 'test@example.com')
        self.assertEqual(test_sig.offset, offset)
        self.assertAlmostEqual(test_sig.time, timestamp, -1)

        # since we defined passed timestamp earlier, test that timestamp is
        # automatically created
        test_sig = utils.make_signature('Tester Test', 'test@example.com')
        self.assertAlmostEqual(test_sig.time, timestamp, delta=10)

    def test_build_path_empty(self):
        # Test building a path from an empty tree
        from gitmodel import utils
        path = '/foo/bar/baz/'  # path sep should be stripped
        # create dummy entry
        blob_oid = self.repo.create_blob("TEST CONTENT")
        entries = [('qux.txt', blob_oid, pygit2.GIT_FILEMODE_BLOB)]
        oid = utils.path.build_path(self.repo, path, entries)
        desc = utils.path.describe_tree(self.repo, oid)
        test_desc = 'foo/\n  bar/\n    baz/\n      qux.txt'
        self.assertMultiLineEqual(desc, test_desc)

    def test_build_path_update(self):
        # Test building a path from an existing tree, updating the path
        from gitmodel import utils
        path = '/foo/bar/baz/'  # path sep should be stripped
        # build initial tree
        blob_oid = self.repo.create_blob("TEST CONTENT")
        entries = [('qux.txt', blob_oid, pygit2.GIT_FILEMODE_BLOB)]
        tree1 = utils.path.build_path(self.repo, path, entries)

        # build the same path, but this time with a new blob
        blob_oid = self.repo.create_blob("UPDATED CONTENT")
        entries = [('qux.txt', blob_oid, pygit2.GIT_FILEMODE_BLOB)]
        tree2 = utils.path.build_path(self.repo, path, entries, tree1)

        entry = self.repo[tree2]['foo/bar/baz/qux.txt']
        new_content = self.repo[entry.oid].data
        desc = utils.path.describe_tree(self.repo, tree2)
        test_desc = 'foo/\n  bar/\n    baz/\n      qux.txt'
        self.assertEqual(new_content, 'UPDATED CONTENT')
        self.assertMultiLineEqual(desc, test_desc)

    def test_glob(self):
        from gitmodel import utils
        tree = self._get_test_tree()
        files = utils.path.glob(self.repo, tree, 'foo/*/*.txt')
        test = ['foo/bar/test.txt', 'foo/bar/test3.txt']
        self.assertEqual(list(files), test)
