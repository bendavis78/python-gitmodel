from gitmodel.test import GitModelTestCase

class GitModelUtilsTest(GitModelTestCase):
    def setUp(self):
        super(GitModelUtilsTest, self).setUp()
        self._repo = self.repo._repo

    def test_describe_tree(self):
        from gitmodel.utils import git
        # build_path test depends on describe_tree, so we build one manually
        repo = self._repo
        # build "/foo/bar/test.txt" and "/foo/bar/baz/test2.txt"
        test2_txt = repo.create_blob("TEST 2")
        baz_tb = repo.TreeBuilder()
        baz_tb.insert('test2.txt', test2_txt, git.GIT_MODE_NORMAL)
        test_txt = repo.create_blob("TEST")
        baz = baz_tb.write()
        bar_tb = repo.TreeBuilder()
        bar_tb.insert('test.txt', test_txt, git.GIT_MODE_NORMAL)
        bar_tb.insert('baz', baz, git.GIT_MODE_TREE)
        bar = bar_tb.write()
        foo_tb = repo.TreeBuilder()
        foo_tb.insert('bar', bar, git.GIT_MODE_TREE)
        foo = foo_tb.write()
        root_tb = repo.TreeBuilder()
        root_tb.insert('foo', foo, git.GIT_MODE_TREE)
        root = root_tb.write()

        desc = git.describe_tree(repo, root)
        test_desc =  'foo/\n bar/\n  baz/\n   test2.txt\n  test.txt'
        self.assertMultiLineEqual(desc, test_desc)
    
    def test_make_signature(self):
        from gitmodel.utils import git
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

        test_sig = git.make_signature('Tester Test', 'test@example.com', timestamp=timestamp)
        self.assertEqual(test_sig.name, 'Tester Test')
        self.assertEqual(test_sig.email, 'test@example.com')
        self.assertEqual(test_sig.offset, offset)
        self.assertAlmostEqual(test_sig.time, timestamp, places=0)
        
        # since we defined passed timestamp earlier, test that timestamp is
        # automatically created
        test_sig = git.make_signature('Tester Test', 'test@example.com')
        self.assertAlmostEqual(test_sig.time, timestamp, delta=10)

    def test_build_path_empty(self):
        # Test building a path from an empty tree
        from gitmodel.utils import git
        path = '/foo/bar/baz/' # path sep should be stripped
        # create dummy entry
        blob_oid = self._repo.create_blob("TEST CONTENT")
        entries = [('qux.txt', blob_oid, git.GIT_MODE_NORMAL)]
        oid = git.build_path(self._repo, path, entries)
        desc = git.describe_tree(self._repo, oid)
        test_desc = 'foo/\n bar/\n  baz/\n   qux.txt'
        self.assertMultiLineEqual(desc, test_desc)
    
    def test_build_path_update(self):
        # Test building a path from an existing tree, updating the path
        from gitmodel.utils import git
        path = '/foo/bar/baz/' # path sep should be stripped
        # build initial tree
        blob_oid = self._repo.create_blob("TEST CONTENT")
        entries = [('qux.txt', blob_oid, git.GIT_MODE_NORMAL)]
        tree1 = git.build_path(self._repo, path, entries)

        # build the same path, but this time with a new blob
        blob_oid = self._repo.create_blob("UPDATED CONTENT")
        entries = [('qux.txt', blob_oid, git.GIT_MODE_NORMAL)]
        tree2 = git.build_path(self._repo, path, entries, tree1)

        new_content = self._repo[tree2]['foo/bar/baz/qux.txt'].to_object().data
        desc = git.describe_tree(self._repo, tree2)
        test_desc = 'foo/\n bar/\n  baz/\n   qux.txt'
        self.assertEqual(new_content, 'UPDATED CONTENT')
        self.assertMultiLineEqual(desc, test_desc)
