===============
python-gitmodel
===============
A distributed, versioned data store for Python
----------------------------------------------

python-gitmodel is a framework for persisting objects using Git for versioning
and remote syncing.

Why?
----
According to Git's README[1], Git is a "stupid content tracker". That means you
aren't limited to storing source code in git. The goal of this project is to
provide an object-level interface to use git as a schema-less data store, as
well as tools that take advantage of gits powerful versioning capabilities.

python-gitmodel is based on libgit2[2], a pure C implementation of the Git core
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


-------------------------------------------------------------------------------

python-gitmodel was inspired by Rick Olson's talk, "Git, the Stupid NoSQL 
Database"[3] and Paul Downman's GitModel[4] for ruby.

-------------------------------------------------------------------------------

.. [1] https://github.com/git/git#readme
.. [2] http://libgit2.github.com
.. [3] http://git-nosql-rubyconf.heroku.com/
.. [4] https://github.com/pauldowman/gitmodel/
