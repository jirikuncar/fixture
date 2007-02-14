
"""Disk I/O-like fixture tools.

An example ...
    
    >>> from fixture import TempIO
    >>> tmp = TempIO()
    >>> assert exists(tmp.putfile('data.txt', 'lots of nonsense'))
    >>> f = tmp.join('data.txt')
    >>> open(f,'r').read()
    'lots of nonsense'
    >>> tmp.incoming = "files/incoming"
    >>> assert tmp.incoming.exists()

"""

__all__ = ['TempIO']

import os, sys
from os import path
from os.path import join, exists, split, basename
from tempfile import mkdtemp
import atexit

_tmpdirs = set()

def _expunge(tmpdir):
    """called internally to remove a tmp dir."""
    if exists(tmpdir):
        import shutil
        shutil.rmtree(tmpdir)
        
def _expunge_all():
    """exit function to remove all registered tmp dirs."""
    for d in _tmpdirs:
        _expunge(d)
    
# this seems to be a safer way to clean up since __del__ can
# be called in a volatile environment :
atexit.register(_expunge_all)

def mkdirall(path, mkdir=os.mkdir):
    """walks the path and makes any non-existant dirs.
    
    optional keyword `mkdir` is the callback for making a single dir
    
    """
    if path[-1] == os.path.sep: 
        path = path[0:-len(os.path.sep)] # trailing slash confused exists()
        
    root = (path[0] == os.path.sep) and os.path.sep or ''
    paths = split(path)[0].split(os.path.sep)
    if len(paths):
        accum = ''
        for p in paths:
            if p is '':
                continue # slash prefix will cause this
            accum = join(accum, p)
            abs = join(root, accum)
            if not exists(abs): mkdir(abs)
    
    mkdir(path)

def putfile(filename, contents, filelike=None, mode=None):
    """opens filename in writing mode, writes contents and closes.
    
    if filelike is None then it will be created with open() and the
    prefixed path will be walked to create non-existant dirs.
    
    """
    if mode is None:
        mode = 'w'
    if filelike is None:
        parent = split(filename)[0]
        if parent and not exists(parent):
            mkdirall(parent)
        filelike = open(filename, mode)
        
    filelike.write(contents)
    filelike.close()
    
class Path(str, object):
    """a directory path.
    
    functions exactly like the builtin str object except it is bound to the 
    following os.path methods:
    
    - abspath()
    - basename()
    - dirname()
    - exists()
    - join(path1, path2, ...)
    - realpath()
    - split()
    - splitext()
    
    """
    def __init__(self, path):
        self._path = path
        self._pnames = (
            'abspath', 'basename', 'dirname', 'exists', 'join', 
            'realpath', 'split', 'splitext')
        str.__init__(self, path)
    
    def __getattribute__(self, n):
        def proxy_to_path(*a,**kw):
            p_method = getattr(os.path, n)
            val = p_method(self._path, *a,**kw)
            if issubclass(type(val), str):
                return self.__class__(val)
            else:
                return val
                
        if not n.startswith('_') and n in self._pnames:
            return proxy_to_path
        else:
            return object.__getattribute__(self, n)
    
class TempIO(object):
    """self-destructing, temporary directory object.
    
    Takes the same keyword args as tempfile.mkdtemp with these additional 
    keywords:
    
    - deferred
    
        - if True, destruction will be put off until atexit.  Otherwise, 
          it will be destructed when it falls out of scope
    
    You will most likely create this in a test module like so 
    (`nosetests`_ style) :
    
        >>> tmp = None
        >>> def setup(self):
        ...     self.tmp = TempIO()
        >>> def teardown(self):
        ...     del self.tmp
        >>> def test_something():
        ...     tmp
        ...     # ...
        >>>
    
    .. _nosetests: http://nose.python-hosting.com/
    
    """
    
    def __init__(self, **kw):
        
        if 'deferred' in kw:
            self._deferred = kw['deferred']
            del kw['deferred']
        else:
            self._deferred = False
        
        if not 'prefix' in kw:
            # a breadcrumb ...
            kw['prefix'] = 'tmp_fixture_'
        
        object.__setattr__(self, 'root', Path(path.realpath(mkdtemp(**kw))))
        _tmpdirs.add(self.root)
    
    
    def __repr__(self):
        return "<%s at '%s'>" % (self.__class__.__name__, self.root)
    
    def __getattr__(self, name):
        try:
            return getattr(self.root, name)
        except AttributeError:
            etype, val, tb = sys.exc_info()
            raise AttributeError(
                    "%s has no attribute %s" % (self, repr(name))), None, tb
    
    def __setattr__(self, name, val):
        if name=='root':
            raise ValueError("cannot set the 'root' attribute")
        if not name.startswith('_'):
            path = self.mkdir(val)
            val = Path(path)
        object.__setattr__(self, name, val)
        
    def __del__(self):
        """removes the root directory and everything under it.
        """
        if self._deferred:
            # let atexit handle it ...
            return
        try:
            _expunge(self.root)
        except:
            # means atexit didn't get it ...
            # this is the last resort.  let this raise an exception?
            # apparently we can even get import errors in __del__,
            # like for shutil.
            pass
    
    def mkdir(self, name):
        """makes a directory in the root and returns its full path.
        
        the path is split each non-existant directory is made.  
        returns full path to new directory.
        
        """
        path = os.path.join(self.root, name)
        mkdirall(path)
        return path
    
    def putfile(self, fname, contents, mode=None):
        """puts new filename relative to your `TempIO` root.
        
        see `mkfile` for how fname is handled.
        
        returns absolute filename.
        """
        relpath, fname = split(fname)
        if relpath and not self.root.join(relpath).exists():
            if relpath.startswith(os.path.sep):
                relpath = relpath[1:]
            self.mkdir(relpath)
            
        f = self.root.join(relpath, fname)
        putfile(f, contents, mode=mode)
        return f
        