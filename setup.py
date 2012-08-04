import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup

setup(
  name='python-gitmodel',
  version='0.1dev',
  test_suite='gitmodel.test',
  packages=['gitmodel'],
  install_requires=['pygit2', 'python-dateutil'],
  license='Creative Commons Attribution-Noncommercial-Share Alike license',
  long_description=open('README.rst').read(),
)
