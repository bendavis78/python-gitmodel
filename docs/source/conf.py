# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# pylint: skip-file

import gitmodel


# -- Project information -----------------------------------------------------

project = gitmodel.__name__
copyright = gitmodel.__copyright__
author = gitmodel.__author__

# The full version, including alpha/beta/rc tags
release = gitmodel.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.githubpages",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_markdown_tables",
    "sphinx_rtd_theme",
    "sphinxcontrib.apidoc",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "./docs",
    "./tests",
    "./setup.py",
]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = [".rst", ".md"]
# source_parsers = {
#     ".md": "recommonmark.parser.CommonMarkParser",
# }

add_module_names = False

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# import sphinx_rtd_theme
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

html_theme_options = {
    # "canonical_url": "",
    # "logo_only": False,
    # "display_version": True,
    # "prev_next_buttons_location": "bottom",
    # "style_external_links": False,
    "style_nav_header_background": "#29BAF4",
    # "collapse_navigation": True,
    # "sticky_navigation": True,
    # "navigation_depth": 4,
    # "includehidden": True,
    # "titles_only": False,
}

# -- apidoc ---------------------------------------------------

apidoc_module_dir = "../.."
apidoc_output_dir = "./generated"
apidoc_excluded_paths = exclude_patterns
apidoc_separate_modules = True
apidoc_toc_file = False
apidoc_module_first = False


# -- autodoc -----------------------------------------------------

autoclass_content = "class"
autodoc_member_order = "bysource"
autodoc_default_flags = ["members"]


# -- napoleon --------------------------------------------

# Parse Google style docstrings.
# See http://google-styleguide.googlecode.com/svn/trunk/pyguide.html
napoleon_google_docstring = True

# Parse NumPy style docstrings.
# See https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt
napoleon_numpy_docstring = True

# Should special members (like __membername__) and private members
# (like _membername) members be included in the documentation if they
# have docstrings.
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True

# If True, docstring sections will use the ".. admonition::" directive.
# If False, docstring sections will use the ".. rubric::" directive.
# One may look better than the other depending on what HTML theme is used.
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False

# If True, use Sphinx :ivar: directive for instance variables:
#     :ivar attr1: Description of attr1.
#     :type attr1: type
# If False, use Sphinx .. attribute:: directive for instance variables:
#     .. attribute:: attr1
#
#        Description of attr1.
#
#        :type: type
napoleon_use_ivar = False

# If True, use Sphinx :param: directive for function parameters:
#     :param arg1: Description of arg1.
#     :type arg1: type
# If False, output function parameters using the :parameters: field:
#     :parameters: **arg1** (*type*) -- Description of arg1.
napoleon_use_param = False

# If True, use Sphinx :rtype: directive for the return type:
#     :returns: Description of return value.
#     :rtype: type
# If False, output the return type inline with the return description:
#     :returns: *type* -- Description of return value.
napoleon_use_rtype = False


# -- autosectionlabel --------------------------------------------

# Prefix document path to section labels, otherwise autogenerated labels would look like
# 'heading' rather than 'path/to/file:heading'
autosectionlabel_prefix_document = True
