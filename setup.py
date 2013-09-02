from distutils.core import setup

setup(
    name='python-gitmodel',
    version='0.1dev',
    test_suite='gitmodel.test',
    packages=['gitmodel'],
    install_requires=['pygit2', 'python-dateutil', 'decorator'],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.rst').read(),
)
