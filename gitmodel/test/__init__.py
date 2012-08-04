import unittest
import inspect
import tempfile
import os
import shutil
import pygit2

class GitModelTestCase(unittest.TestCase):
    """ Sets up a temporary git repository for each test """

    def setUp(self):
        # For tests, it's easier to use global_config so that we don't
        # have to pass a config object around.
        from gitmodel.conf import global_settings
        from gitmodel import exceptions
        from gitmodel import utils

        self.config = global_settings
        self.config.REPOSITORY_PATH = tempfile.mkdtemp()

        self.exceptions = exceptions
        self.utils = utils

        # gitmodel does not create your repo for you
        self.repo = pygit2.init_repository(self.config.REPOSITORY_PATH, False)
        self.index = self.repo.index
        self.index.read()

    def tearDown(self):
        # clean up test repo
        shutil.rmtree(self.config.REPOSITORY_PATH)


def get_module_suite(mod):
    """
    Test modules may provide a suite() function, otherwise all TestCase 
    subclasses are gethered automatically into a TestSuite
    """
    # modules may provide a suite() function,
    if hasattr(mod, 'suite'):
        return mod.suite()
    else:
        # gather all testcases in this module into a suite
        suite = unittest.TestSuite()
        for name in dir(mod):
            obj = getattr(mod, name)
            if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
                suite.addTest(unittest.makeSuite(obj))
        # Set a name attribute so we can find it later
        suite.name = mod.__name__.split('.')[-2]
        suite.module = mod
        return suite


def get_all_suites():
    """ Yields all testsuites """
    # Tests can be one of:
    # - test/suitename/tests.py
    # - test/suitename_tests.py
    test_dir = os.path.dirname(__file__)
    for f in os.listdir(test_dir):
        mod = None
        if os.path.exists(os.path.join(test_dir, f, 'tests.py')): 
            p = __import__('gitmodel.test.{}'.format(f), globals(), locals(), ['tests'], -1)
            mod = p.tests
        elif f.endswith('_tests.py'):
            modname = f.replace('.py', '')
            p = __import__('gitmodel.test', globals(), locals(), [modname], -1)
            mod = getattr(p, modname)
        if mod:
            suite = get_module_suite(mod)
            yield suite

def default_suite():
    """ Sets up the default test suite """
    suite = unittest.TestSuite()
    for other_suite in get_all_suites():
        suite.addTest(other_suite)
    return suite


class TestLoader(unittest.TestLoader):
    """ Allows tests to be referenced by name """
    def loadTestsFromName(self, name, module=None):
        if name == 'suite':
            return default_suite()

        testcase = None
        if '.' in name:
            name, testcase = name.rsplit('.',1)
        
        for suite in get_all_suites():
            if suite.name == name:
                if testcase is None:
                    return suite
                return super(TestLoader, self).loadTestsFromName(testcase, suite.module)

        raise LookupError('could not find test case for "{}"'.format(name))

def main():
    """ Runs the default test suite as a command line application. """
    unittest.main(__name__, testLoader=TestLoader(), defaultTest='suite')
