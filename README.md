# python-gitmodel

[![PyPI version](https://badge.fury.io/py/gitarmony-python.svg)](https://badge.fury.io/py/gitarmony-python)
[![Documentation Status](https://readthedocs.org/projects/gitarmony-python/badge/?version=latest)](https://gitarmony-python.readthedocs.io/en/latest)
[![codecov](https://codecov.io/gh/bendavis78/python-gitmodel/branch/master/graph/badge.svg?token=5267NA3EQQ)](https://codecov.io/gh/bendavis78/python-gitmodel)

## A distributed, versioned data store for Python

python-gitmodel is a framework for persisting objects using Git for
versioning and remote syncing.

## Why?

According to [Git's README](<https://github.com/git/git#readme>), Git
is a \"stupid content tracker\". That means you aren\'t limited to
storing source code in git. The goal of this project is to provide an
object-level interface to use git as a schema-less data store, as well
as tools that take advantage of git\'s powerful versioning capabilities.

python-gitmodel allows you to model your data using python, and provides
an easy-to-use interface for storing that data as git objects.

python-gitmodel is based on [libgit2](<http://libgit2.github.com>), a
pure C implementation of the Git core methods. This means that instead
of calling git commands via shell, we get to use git at native speed.

## What\'s so great about it?

* Schema-less data store
* Never lose data. History is kept forever and can be restored using
* git tools.
* Branch and merge your production data
    * gitmodel can work with different branches
    * branch or tag snapshots of your data
    * experiment on production data using branches, for example, to test a migration
* Ideal for content-driven applications

## Example usage

Below we\'ll cover a use-case for a basic flat-page CMS.

Basic model creation:
```python
 from gitmodel.workspace import Workspace from gitmodel import fields  ws = Workspace('path/to/my-repo/.git')  class Page(ws.GitModel):     slug = fields.SlugField()      title = fields.CharField()     content = fields.CharField()     published = fields.BooleanField(default=True)
 ```

The Workspace can be thought of as your git working directory. It also
acts as the \"porcelain\" layer to pygit2\'s \"plumbing\". In contrast
to a working directory, the Workspace class does not make use of the
repository\'s INDEX and HEAD files, and instead keeps track of these in
memory.

Saving objects:
```python
 page = Page(slug='example-page', title='Example Page') page.content = '<h2>Here is an Example</h2><p>Lorem Ipsum</p>' page.save()  print(page.id) # abc99c394ab546dd9d6e3381f9c0fb4b
 ```

By default, objects get an auto-ID field which saves as a python UUID
hex (don\'t confuse these with git hashes). You can easily customize
which field in your model acts as the ID field, for example:
```python
 class Page(ws.GitModel):     slug = fields.SlugField(id=True)  # OR  class Page(ws.GitModel):     slug = fields.SlugField()      class Meta:         id_field = 'slug'
 ```

Objects are not committed to the repository by default. They are,
however, written into the object database as trees and blobs. The
[Workspace.index]{.title-ref} object is a [pygit2.Tree]{.title-ref} that
holds the uncommitted data. It\'s analagous to Git\'s index, except that
the pointer is stored in memory.

Creating commits is simple:
```python
 oid = page.save(commit=True, message='Added an example page') commit = ws.repo[oid] # a pygit2.Commit object print(commit.message)
 ```

You can access previous commits using pygit2, and even view diffs
between two versions of an object.
```python
 # walking commits for commit in ws.walk():     print("{}: {}".format(commit.hex, commit.message))   # get a diff between two commits head_commit = ws.branch.commit prev_commit_oid = head_commit.parents[0] print(prev_commit.diff(head_commit))
 ```

Objects can be easily retrieved by their id:
```python
 page = Page.get('example-page') print(page.content)
 ```

# Caveat Emptor

Git doesn\'t perform very well on its own. If you need your git-backed
data to perform well in a production environment, you need to get it a
\"wingman\". Since python-gitmodel can be used in a variety of ways,
it\'s up to you to decide the best way to optimize it.

# Status

This project is no longer under active development.

# TODO

* Caching?
* Indexing?
* Query API?
* Full documentation

python-gitmodel was inspired by Rick Olson\'s talk, \"[Git, the Stupid
NoSQL Database](<http://git-nosql-rubyconf.heroku.com/>)\" and Paul
Downman\'s [GitModel](<https://github.com/pauldowman/gitmodel/>) for
ruby.

# Development

This projects requires the following:

-   [Python >=3.7.9](https://www.python.org/downloads/release/python-379/)
-   [virtualenwrapper](https://pypi.org/project/virtualenvwrapper/) (macOS/Linux)
-   [virtualenwrapper-win](https://pypi.org/project/virtualenvwrapper-win/) (Windows)

Make sure your `WORKON_HOME` environment variable is set on Windows, and create a `gitmodel` virtual environment with `mkvirtualenv`.
Build systems for installing requirements and running tests are on board of the SublimeText project.
