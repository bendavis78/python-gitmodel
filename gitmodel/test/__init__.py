import unittest
import inspect
import os

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
        return suite


def get_all_suites():
    """ Yields all testsuites """
    # Tests are organized as test/suitename/tests.py
    test_dir = os.path.dirname(__file__)
    for f in os.listdir(test_dir):
        if os.path.exists(os.path.join(test_dir, f, 'tests.py')): 
            mod = __import__('gitmodel.test.{}'.format(f), globals(), locals(), ['tests'], -1)
            suite = get_module_suite(mod.tests)
            yield suite


def suite():
    """ Sets up the default test suite """
    suite = unittest.TestSuite()
    for other_suite in get_all_suites():
        suite.addTest(other_suite)
    return suite

def main():
    """ Runs the default test suite as a command line application. """
    unittest.main(__name__, defaultTest='suite')
