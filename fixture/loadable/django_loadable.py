"""Components for loading and unloading data using
`Django's ORM <http://www.djangoproject.com>`_.

See :ref:`Using Fixture With Django<using-fixture-with-django>` for a complete example.
"""

from fixture.loadable import DBLoadableFixture
from itertools import tee

__all__ = ('DjangoMedium', 'DjangoFixture', 'DjangoEnv')

DJANGO_ENV_SPLIT = '__'

pretty_mod_name = lambda model: '.'.join([model._meta.app_label,
                                          model._meta.object_name])

class DjangoMedium(DBLoadableFixture.StorageMediumAdapter):
    """Adapter for storing data using django models
    """
    
    def clear(self, obj):
        """Delete this object from the DB
        
        :param obj: The object to delete
        :type obj: A django model
        """
        obj.delete()
        
    def _check_schema(self, column_vals):
        """Check that the column_vals given match up to this model's schema
        
        :param column_vals: The parsed column values
        :type column_vals: tuple of field_name, field_value
        :raises: ValueError
        """
                    
        model = self.medium
        # This will include reverse relation names, and m2ms
        all_field_names = set(model._meta.get_all_field_names())
        # This will be only localy defined fields (excluding many_to_many)
        own_field_names = set([f.name for f in model._meta.fields])
        # All locally defined fields which are required and not auto fields (id)
        required_field_names = set([f.name for f in model._meta.fields
                                    if not f.null
                                    and not f.primary_key])
        m2m_field_names = set([f.name for f in model._meta.many_to_many])
        related_field_names =  set([ro.field.related_query_name() for ro in
                                model._meta.get_all_related_many_to_many_objects() \
                                + model._meta.get_all_related_objects()])
        
        for key, val in column_vals:
            # Valid field?
            if not key in own_field_names.union(m2m_field_names):
                msg = "Model %r doesn't have field named %s." % \
                                    (pretty_mod_name(model), key)
                try: # Provide a nicer error message
                    if key in related_field_names:
                        # {reverse_related_name: RelatedObject}
                        fld_lookup = dict([(ro.field.related_query_name(), ro) \
                                                for ro in
                                    model._meta.get_all_related_many_to_many_objects() \
                                    + model._meta.get_all_related_objects()])
                        other_model = fld_lookup[key].model
                        fld_name = fld_lookup[key].field.name
                        info = ("\n**********************\n"
                                "This is a reverse relation of %s, you "
                                "should specifiy it there, i.e:\n"
                                "    %sData(DataSet):\n"
                                "        class ...:\n"
                                "            %s = [...]\n"
                                "**********************\n" % \
                                ("%s.%s" % (pretty_mod_name(other_model), fld_name),
                                 other_model.__name__,
                                 fld_name))
                        msg += info
                except:
                    raise#pass
                raise ValueError(msg)
                
            # Keep a track of required fields
            try:
                required_field_names.remove(key)
            except KeyError:
                pass
            
            # If the field is a relation check the related type
            field = model._meta.get_field(key)
            from django.db.models.fields.related import RelatedField
            if isinstance(field, RelatedField):
                try:
                    len(val)
                except TypeError:
                    val = [val]
                rel_types = [isinstance(v, field.rel.to) for v in val]
                if not field.null and False in rel_types:
                    raise ValueError("Values for field %s must be of type %s, "
                                     "got %s" % \
                                     (key,
                                      pretty_mod_name(field.rel.to),
                                      val))
        if len(required_field_names):
            raise ValueError("Requred fields %s not found" % required_field_names)
        return m2m_field_names
    
    def save(self, row, column_vals):
        """Save this row to the DB"""
        model = self.medium
        manager = self.medium._default_manager
        field_names = [f.name for f in model._meta.fields]
        column_vals = list(column_vals)
        m2m_field_names = self._check_schema(column_vals[:])
        # This will take care of foreignkeys too
        dbvals = {}
        for key, val in column_vals:
            if key in field_names:
                dbvals[key] = val
        new_obj = manager.get_or_create(**dbvals)[0]
        columns = dict(column_vals)
        for m2m in m2m_field_names:
            if m2m in columns:
                getattr(new_obj, m2m).add(*columns[m2m])
        return new_obj
        
    
    def visit_loader(self, loader):
        """Visit the loader and store a reference to the transaction connection"""
        self.transaction = loader.transaction

class DjangoFixture(DBLoadableFixture):
    """A fixture that knows how to load DataSet objects via `Django Model`_ classes.
    """
            
    def __init__(self, **kw):
        if not kw.get('env', None):
            kw['env'] = DjangoEnv
        DBLoadableFixture.__init__(self, **kw)
    
    DjangoMedium = DjangoMedium
    Medium = DjangoMedium
    
    def create_transaction(self):
        """Return a new transaction
        
        Calls enter_transaction_management and returns the django.db.transaction
        module (which meets the API required by fixture)
        """
        from django.db import transaction
        transaction.enter_transaction_management()
        return transaction
    
    def then_finally(self, unloading=False):
        """Not sure if this is needed, leaving it in for a reminder"""
        from django.db import transaction
        try:
            self.transaction.leave_transaction_management()
        except transaction.TransactionManagementError, e:
            raise
        
class DjangoEnv(object):
    """
    A wrapper around get_models to allow lookup from DataSet's class name
    
    """
    
    @staticmethod
    def get(name, default=None):
        """Fetch this name from django's cache
        
        :param name: A name like app__ModelName such that name.split('__')
            will give you an app label and a model name suitable for get_model
        """
        from django.db.models.loading import get_model
        try:
            app_label, model_name = name.split(DJANGO_ENV_SPLIT)
        except ValueError:
            raise ValueError("name must be splittable by %s, got %s" % \
                                (DJANGO_ENV_SPLIT, name))
        else:
            return get_model(app_label, model_name)
        
        