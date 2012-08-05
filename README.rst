===============
python-gitmodel
===============
A distributed, versioned data store for Python
----------------------------------------------

python-gitmodel is a framework for persisting objects using Git for versioning
and remote syncing.

Why?
----
According to `Git's README`_, Git is a "stupid content tracker". That means you
aren't limited to storing source code in git. The goal of this project is to
provide an object-level interface to use git as a schema-less data store, as
well as tools that take advantage of git's powerful versioning capabilities.

python-gitmodel is based on `libgit2`_, a pure C implementation of the Git core
methods. This means that instead of calling git commands via shell, we get
to use git at native speed.

What it's good for
------------------
* Schema-less data store
* Never lose data. History is kept forever and can be restored using git tools.
* Branch and merge your production data
  * python-gitmodel can work with different branches
  * branch or tag snapshots of your data
  * experiment on production data using branches, for example, to test a migration

Status
------
This project is under heavy development, and the API will likely change
drastically before a 1.0 release. Currently only basic model creation
and saving instances will work. 

TODO
----
* Field validation
* Caching
* Indexing
* Query API
* Versioning utilities (branching/merging)
* TreeGitModel (stores objects in hierarchical structure)

-------------------------------------------------------------------------------

python-gitmodel was inspired by Rick Olson's talk, "`Git, the Stupid NoSQL 
Database`_" and Paul Downman's `GitModel`_ for ruby.

.. _Git's README: https://github.com/git/git#readme
.. _libgit2: http://libgit2.github.com
.. _Git, the Stupid NoSQL Database: http://git-nosql-rubyconf.heroku.com/
.. _GitModel: https://github.com/pauldowman/gitmodel/
