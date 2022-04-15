import unittest
import inspect
import tempfile
import os
import re
import shutil
import pygit2
import logging


class GitModelTestCase(unittest.TestCase):
    """Sets up a temporary git repository for each test"""

    def setUp(self):
        # For tests, it's easier to use global_config so that we don't
        # have to pass a config object around.
        from gitmodel.workspace import Workspace
        from gitmodel import exceptions
        from gitmodel import utils

        self.exceptions = exceptions
        self.utils = utils

        # Create temporary repo to work from
        self.repo_path = tempfile.mkdtemp(prefix="python-gitmodel-")
        pygit2.init_repository(self.repo_path, False)
        self.workspace = Workspace(self.repo_path)

    def tearDown(self):
        # clean up test repo
        try:
            shutil.rmtree(self.repo_path)
        except PermissionError as error:
            logging.error(error)


