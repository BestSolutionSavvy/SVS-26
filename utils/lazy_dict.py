class LazyDict(dict):
    def __init__(self, resolvers: dict):
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
        try:
            return self[key]
        except KeyError:
            return default

    def get_cached_dict(self) -> dict:
        return dict(self)