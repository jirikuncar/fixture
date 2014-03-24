import ast
import ez_setup
ez_setup.use_setuptools()
import os
import re
import pydoc
import sys

from setuptools import setup, find_packages

# Get the version string.  Cannot be done with import!
with open(os.path.join('fixture', 'version.py'), 'rt') as f:
    version = re.search(
        '__version__\s*=\s*"(?P<version>.*)"\n',
        f.read()
    ).group('version')

def get_module_meta(modfile):
    with open(modfile) as f:
        doc = ast.get_docstring(ast.parse(f.read()))
    if doc is None:
        raise RuntimeError(
            "could not parse doc string from %s" % modfile)
    return pydoc.splitdoc(doc)

description, long_description = get_module_meta(
    os.path.join('fixture', '__init__.py'))

setup(
    name='fixture',
    version=version,
    author='Kumar McMillan',
    author_email='kumar dot mcmillan / gmail.com',
    description=description,
    classifiers=[ 'Environment :: Other Environment',
                  'Intended Audience :: Developers',
                  ('License :: OSI Approved :: GNU Library or Lesser '
                   'General Public License (LGPL)'),
                  'Natural Language :: English',
                  'Operating System :: OS Independent',
                  'Programming Language :: Python',
                  'Topic :: Software Development :: Testing',
                  'Topic :: Software Development :: Quality Assurance',
                  'Topic :: Utilities'],
    long_description=long_description,
    license='GNU Lesser General Public License (LGPL)',
    keywords=('test testing tools unittest fixtures setup teardown '
              'database stubs IO tempfile'),
    url='http://farmdev.com/projects/fixture/',

    packages=find_packages(),
    install_requires=['six'],
    entry_points={
        'console_scripts': ['fixture = fixture.command.generate:main'],
    },
    # the following allows e.g. easy_install fixture[django]
    extras_require={
        'decorators': ['nose>=0.9.2'],
        'sqlalchemy': ['SQLAlchemy>=0.4'],
        'sqlobject': ['SQLObject==0.8'],
        'django': ['django'],
    },
    test_suite='nose.collector',
    tests_require=['nose', 'coverage'],
)
