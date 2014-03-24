
"""Loadable fixture components"""

from __future__ import absolute_import

__all__ = ['SQLAlchemyFixture', 'SQLObjectFixture', 'GoogleDatastoreFixture',
           'DjangoFixture', 'StormFixture']

from fixture.loadable import loadable
__doc__ = loadable.__doc__

from sqlalchemy_loadable import SQLAlchemyFixture
from sqlobject_loadable import SQLObjectFixture
from google_datastore_loadable import GoogleDatastoreFixture
from django_loadable import DjangoFixture
from storm_loadable import StormFixture

