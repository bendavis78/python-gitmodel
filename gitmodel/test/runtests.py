#!/usr/bin/env python
import unittest

tests = ('basic',)

if __name__ == "__main__":
    for mod in tests:
        unittest.main('{}.tests'.format(mod), exit=False)
