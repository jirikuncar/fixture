
"""representations of data."""

from fixture.util import ObjRegistry

def lazy_meta(obj):
    # if not hasattr(obj, 'meta'):
    try:
        object.__getattribute__(obj, 'meta')
    except AttributeError:
        Meta = object.__getattribute__(obj, 'Meta')
        object.__setattr__(obj, 'meta', Meta())

class DataContainer(object):
    """contains data accessible by attribute and/or key.
    
    for all internally used attributes, use the inner class Meta.
    """
    _reserved_attr = ('meta', 'Meta', 'ref', 'get')
    class Meta:
        data = None
        keys = None
        
    def __init__(self, data=None, keys=None):
        lazy_meta(self)
        if not data: 
            data = {}
        self.meta.data = data
        if not keys: 
            keys = []
        self.meta.keys = keys
    
    def __contains__(self, name):
        return name in self.meta.data
    
    def __getitem__(self, key):
        return self.meta.data[key]
        
    def __getattribute__(self, name):
        
        # it is necessary to completely override __getattr__
        # so that class attributes don't interfer
        if name.startswith('_') or name in self._reserved_attr:
            return object.__getattribute__(self, name)
        try:
            return self.meta.data[name]
        except KeyError:
            raise AttributeError("%s has no attribute '%s'" % (self, name))
    
    def __repr__(self):
        if hasattr(self, 'meta'):
            keys = self.meta.keys
        else:
            keys = None
        return "<%s at %s with keys %s>" % (
                self.__class__.__name__,
                hex(id(self)), keys)
    
    def get(self, k, default=None):
        return self.meta.data.get(k, default)
    
    def _setdata(self, key, value):
        if key not in self.meta.data:
            self.meta.keys.append(key)
        self.meta.data[key] = value

class DataRow(DataContainer):
    """a key/attribute accessible dictionary."""
    _reserved_attr = DataContainer._reserved_attr + ('iteritems', 'items')
    class Meta(DataContainer.Meta):
        pass
    
    def __init__(self, data):
        DataContainer.__init__(self, data=data, keys=[k for k in data])
    
    def __iter__(self):
        for k in self.meta.data:
            yield k
    
    def iteritems(self):
        for k,v in self.meta.data.items():
            yield (k,v)
    
    def items(self):
        for k,v in self.iteritems():
            yield (k,v)

class DataSetContainer(object):
    """yields datasets when itered over."""
    class Meta:
        datasets = None
        dataset_keys = None
        
    def __init__(self):
        lazy_meta(self)
        self.meta.datasets = {}
        self.meta.dataset_keys = []
        self.meta._cache = ObjRegistry()
    
    def __iter__(self):
        for k in self.meta.dataset_keys:
            yield self.meta.datasets[k]
        
    def _dataset_to_key(self, dataset):
        return dataset.__class__.__name__
        
    def _setdataset(self, dataset, key=None, isref=False):
        
        # due to reference resolution we might get colliding data sets...
        if dataset in self.meta._cache:
            return False
            
        if key is None:
            key = self._dataset_to_key(dataset)
        if not isref:
            # refs are not yielded
            self.meta.dataset_keys.append(key)
            
        self.meta.datasets[key] = dataset
        
        self.meta._cache.register(dataset)
        return True

class SuperSet(DataContainer, DataSetContainer):
    """a set of data sets.
    
    each attribute/key is a DataSet.
    """
    class Meta(DataContainer.Meta, DataSetContainer.Meta):
        pass
        
    def __init__(self, *datasets):
        DataContainer.__init__(self)
        DataSetContainer.__init__(self)
        self._store_datasets(datasets)
    
    def _store_datasets(self, datasets):
        for d in datasets:
            k = self._dataset_to_key(d)
            self._setdata(k, d)
            self._setdataset(d, key=k)
            
            for ref_d in d.ref:
                k = self._dataset_to_key(ref_d)
                self._setdata(k, ref_d)
                self._setdataset(ref_d, key=k, isref=True)

class MergedSuperSet(SuperSet):
    """a collection of data sets.
    
    all attributes of all data sets are merged together.
    """
    class Meta(SuperSet.Meta):
        pass
    def __init__(self, *datasets):
        lazy_meta(self)
        self.meta.keys_to_datasets = {}
        SuperSet.__init__(self, *datasets)
    
    def _setdataset(self, dataset, key=None, isref=False):
        if SuperSet._setdataset(self, dataset, key=key, isref=isref):
            for k,row in dataset:
                if k in self.meta.keys_to_datasets:
                    raise ValueError(
                        "cannot add key '%s' for %s because it was "
                        "already added by %s" % (
                            k, dataset, self.meta.keys_to_datasets[k]))
                self._setdata(k, row)
                self.meta.keys_to_datasets[k] = dataset 
    
    def _store_datasets(self, datasets):    
        for dataset in datasets:
            self._setdataset(dataset)
            
            for d in dataset.ref:
                self._setdataset(d, isref=True)

class Ref(object):
    """A reference to a row in a DataSet class."""
    class Value(object):
        def __init__(self, ref, attr_name):
            self.ref = ref
            self.value = ref.getvalue(attr_name)
            
    def __init__(self, dataset_class, row):
        self.dataset_class = dataset_class
        self.row = row
    
    def __call__(self, ref_name):
        return self.Value(self, ref_name)
    
    def __repr__(self):
        return "<%s to %s.%s at %s>" % (
            self.__class__.__name__, self.dataset_class.__name__, 
            self.row.__name__, hex(id(self)))
    
    def getvalue(self, attr_name):
        return getattr(self.row, attr_name)

from types import ClassType
def is_row_class(attr):
    return (type(attr)==ClassType and attr.__name__ != 'Meta' and 
            not issubclass(attr, DataContainer.Meta))
    
class DataType(type):
    def __init__(cls, name, bases, cls_attr):
        super(DataType, cls).__init__(name, bases, dict)
        for name, attr in cls_attr.iteritems():
            if is_row_class(attr):
                # bind a ref method
                attr.ref = Ref(cls, attr)

class DataSet(DataContainer):
    """a set of row objects.
    
    Keyword Arguments
    -----------------
    - default_refclass
      
      - a SuperSet to use if None has already been specified in Meta
    
    a loader will typically want to load a dataset into a 
    single storage medium.  I.E. a table in a database.
    
    >>> from fixture import DataSet
    >>> class Flowers(DataSet):
    ...     class violets:
    ...         color = 'blue'
    ...     class roses:
    ...         color = 'red'
    ... 
    >>> f = Flowers()
    >>> f.violets.color
    'blue'
    >>> f.violets['color']
    'blue'
    
    """
    __metaclass__ = DataType
    _reserved_attr = DataContainer._reserved_attr + ('data',)
    ref = None
    class Meta(DataContainer.Meta):
        row = DataRow
        refclass = None
        loader = None
        storage = None
        storage_medium = None
        stored_objects = []
        references = []
        _built = False
    
    def __init__(self, default_refclass=None):
        DataContainer.__init__(self)
        
        # we want the convenience of not having to 
        # inherit DataSet.Meta.  hmmm ...
        if not isinstance(self.meta, DataSet.Meta):
            defaults = DataSet.Meta()
            for name in dir(defaults):
                if not hasattr(self.meta, name):
                    setattr(self.meta, name, getattr(defaults, name))
        
        self.meta.stored_objects = []
        # dereference from class ...        
        try:
            cl_attr = getattr(self.Meta, 'references')
        except AttributeError:
            cl_attr = []
        setattr(self.meta, 'references', [c for c in cl_attr])
        
        if not self.meta.refclass:
            if default_refclass:
                self.meta.refclass = default_refclass
            else:
                self.meta.refclass = SuperSet
        
        def mkref(references):
            return self.meta.refclass(*[
                        ds(default_refclass=default_refclass) \
                            for ds in iter(references)])
        
        # data def style classes, so they have refs when data is walked
        if len(self.meta.references) > 0:
            self.ref = mkref(self.meta.references)
            
        for key, data in self.data():
            if key in self:
                raise ValueError(
                    "data() cannot redeclare key '%s' "
                    "(this is already an attribute)" % key)
            self._setdata(key, self.meta.row(data))
            
        if not self.ref:
            # type style classes, since refs are now discovered
            self.ref = mkref(self.meta.references)
    
    def __iter__(self):
        for key in self.meta.keys:
            yield (key, getattr(self, key))
    
    def data(self):
        """returns iterable key/dict pairs.                     
        """
        if self.meta._built:
            for k,v in self:
                yield (k,v)
                
        def public_dir(obj):
            for name in dir(obj):
                if name.startswith("_"):
                    continue
                yield name
                
        empty = True
        for name in public_dir(self.__class__):
            val = getattr(self.__class__, name)
            if not is_row_class(val):
                continue
            
            empty = False
            key = name
            row_class = val
            row = {}
            
            for col_name in public_dir(row_class):
                col_val = getattr(row_class, col_name)
                
                if isinstance(col_val, Ref):
                    continue
                if isinstance(col_val, Ref.Value):
                    ref = col_val.ref
                    col_val = col_val.value
                    if ref.dataset_class not in self.meta.references:
                        # store the reference:
                        self.meta.references.append(ref.dataset_class)
                
                row[col_name] = col_val
            yield (key, row)
            
        if empty:
            raise ValueError("cannot create an empty DataSet")
        self.meta._built = True