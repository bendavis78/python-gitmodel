from gitmodel.test import GitModelTestCase
from gitmodel import exceptions

class GitModelWorkspaceTest(GitModelTestCase):
    def setUp(self):
        super(GitModelWorkspaceTest, self).setUp()
        self.repo = self.workspace.repo

    def test_workspace_init(self):
        from gitmodel.conf import Config
        import pygit2
        self.assertIsInstance(self.workspace.config, Config)
        self.assertIsInstance(self.workspace.repo, pygit2.Repository)

    def test_default_branch(self):
        # make sure head matches default branch
        default_branch = self.workspace.config.DEFAULT_BRANCH
        self.assertEqual(self.workspace.head, default_branch)
        self.assertIsNotNone(self.workspace.index)
    
    def test_base_gitmodel(self):
        from gitmodel.models import GitModel
        self.assertTrue(issubclass(self.workspace.GitModel, GitModel))
        test_model = self.workspace.GitModel()
        self.assertIsInstance(test_model, self.workspace.GitModel)
        self.assertIsInstance(test_model, GitModel)
        self.assertEqual(test_model._meta.workspace, self.workspace)

    def test_init_existing_branch(self):
        from gitmodel.workspace import Workspace
        # Test init of workspace with existing branch
        # create a commit on existing workspace
        self.workspace.add_blob('test.txt', 'Test')
        self.workspace.commit('initial commit')
        new_workspace = Workspace(self.workspace.repo.path)
        self.assertEqual(new_workspace.branch.ref.name, 'refs/heads/master')
        self.assertEqual(new_workspace.branch.commit.message, 'initial commit')

    def test_getitem(self):
        self.workspace.add_blob('test.txt', 'Test')
        self.assertEqual(self.workspace.index['test.txt'].to_object().data, 'Test')

    def test_branch_property(self):
        self.assertIsNone(self.workspace.branch)
        self.workspace.add_blob('test.txt', 'Test')
        self.workspace.commit('initial commit')
        self.assertIsNotNone(self.workspace.branch)
        self.assertEqual(self.workspace.branch.ref.name, 'refs/heads/master')
        self.assertEqual(self.workspace.branch.commit.message, 'initial commit')

    def test_set_branch(self):
        # create intial master branch
        self.workspace.add_blob('test.txt', 'Test')
        self.workspace.commit('initial commit')
        # create a new branch
        self.workspace.create_branch('testbranch')
        # set_branch will automatically update the index
        self.workspace.set_branch('testbranch')
        self.workspace.add_blob('test.txt', 'Test 2')
        self.workspace.commit('test branch commit')

        test_content = self.workspace.index['test.txt'].to_object().data
        self.assertEqual(test_content, 'Test 2')

        self.workspace.set_branch('master')
        test_content = self.workspace.index['test.txt'].to_object().data
        self.assertEqual(test_content, 'Test')

    def test_set_nonexistant_branch(self):
        with self.assertRaisesRegexp(exceptions.RepositoryError, r'Reference not found'):
            self.workspace.set_branch('foobar')

    def test_update_index_with_pending_changes(self):
        self.workspace.add_blob('test.txt', 'Test')
        self.workspace.commit('initial commit')
        with self.assertRaisesRegexp(exceptions.RepositoryError, r'pending'):
            self.workspace.add_blob('test.txt', 'Test 2')
            self.workspace.create_branch('testbranch')
            self.workspace.set_branch('testbranch')
    
    def test_add_blob(self):
        self.workspace.add_blob('test.txt', 'Test')
        self.assertEqual(self.workspace.index['test.txt'].to_object().data, 'Test')

    def test_commit_on_success(self):
        with self.workspace.commit_on_success('Test commit'):
            self.workspace.add_blob('test.txt', 'Test')
        self.assertEqual(self.workspace.branch.commit.message, 'Test commit')

    def test_commit_on_success_with_error(self):
        # make an exception we can catch
        class TestException(Exception): pass
        try:
            with self.workspace.commit_on_success('Test commit'):
                self.workspace.add_blob('test.txt', 'Test')
                raise TestException('dummy error')
        except TestException:
            pass
        # since commit should have failed, current branch should be nonexistent
        self.assertEqual(self.workspace.branch, None)

    def test_commit_on_success_with_pending_changes(self):
        self.workspace.add_blob('foo.txt', 'Foobar')
        with self.assertRaisesRegexp(exceptions.RepositoryError, r'pending'):
            with self.workspace.commit_on_success('Test commit'):
                self.workspace.add_blob('test.txt', 'Test')
        self.assertEqual(self.workspace.branch, None)
        
    def test_has_changes(self):
        self.workspace.add_blob('foo.txt', 'Foobar')
        self.assertTrue(self.workspace.has_changes())
