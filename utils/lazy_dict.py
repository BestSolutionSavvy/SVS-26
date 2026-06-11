class LazyDict(dict):
    """A dictionary that lazily computes values using provided resolvers."""
    
    def __init__(self, resolvers: dict):
        """
        Initialize a LazyDict with a dictionary of resolvers.
        
        Parameters
        -------
        resolvers: dict
            A dictionary mapping keys to resolver functions or values. If the resolver is a function, 
            it will be called to compute the value when the key is accessed for the first time.
        """
        dict.__init__(self)
        self._resolvers = resolvers
        self._accessed_keys = set()

    def __missing__(self, key):
        if key not in self._resolvers:
            raise KeyError(key)
        resolver = self._resolvers[key]
        value = resolver() if callable(resolver) else resolver
        self[key] = value
        return value
    
    def __getitem__(self, key):
        if key in self:
            self._accessed_keys.add(key)
            return super().__getitem__(key)
        return self.__missing__(key)

    def get(self, key, default=None):
        """Get the value for key if key is in the dictionary, else default."""
        try:
            return self[key]
        except KeyError:
            return default

    def get_cached_dict(self) -> dict:
        """Get a regular dictionary with all currently accessed keys and their values."""
        return dict(self)