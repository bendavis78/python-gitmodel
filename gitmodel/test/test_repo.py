from gitmodel.test import GitModelTestCase

class GitModelRepoTest(GitModelTestCase):
    def setUp(self):
        super(GitModelRepoTest, self).setUp()
        self._repo = self.repo._repo

    def test_init_new(self):
        # Test init of fresh repository
        self.assertTrue(False)
    
    def test_init_existing_branch(self):
        # Test init of repo with existing branch
        self.assertTrue(False)

    def test_getitem(self):
        self.assertTrue(False)

    def test_branch_property(self):
        self.assertTrue(False)

    def test_update_index(self):
        self.assertTrue(False)
    
    def test_add(self):
        self.assertTrue(False)

    def test_add_blob(self):
        self.assertTrue(False)

    def test_commit_on_success(self):
        self.assertTrue(False)

     
