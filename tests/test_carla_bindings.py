"""Test cases for CARLA bindings."""
from carla_bindings import LazyDict


def test_get_cached_dict_returns_normal_dict():
    """Test that get_cached_dict returns a normal dict, not a LazyDict."""
    resolvers = {
        'a': lambda: 10,
        'b': lambda: 20,
    }
    lazy_dict = LazyDict(resolvers)
    
    # Access some values to populate the cache
    lazy_dict['a']
    lazy_dict['b']
    
    # Get the cached dict
    cached = lazy_dict.get_cached_dict()
    
    # Verify it's a regular dict, not a LazyDict
    assert isinstance(cached, dict)
    assert not isinstance(cached, LazyDict)
    assert type(cached) == dict


def test_get_cached_dict_contains_accessed_values():
    """Test that get_cached_dict contains all accessed values."""
    resolvers = {
        'x': lambda: 100,
        'y': lambda: 200,
        'z': lambda: 300,
    }
    lazy_dict = LazyDict(resolvers)
    
    # Access some values
    _ = lazy_dict['x']
    _ = lazy_dict['y']
    
    cached = lazy_dict.get_cached_dict()
    
    # Verify accessed values are in the cached dict
    assert cached == {'x': 100, 'y': 200}


def test_get_cached_dict_with_all_values_accessed():
    """Test get_cached_dict after accessing all values."""
    resolvers = {
        'speed': 50,
        'distance': 25.5,
        'name': 'vehicle',
    }
    lazy_dict = LazyDict(resolvers)
    
    # Access all values
    _ = lazy_dict['speed']
    _ = lazy_dict['distance']
    _ = lazy_dict['name']
    
    cached = lazy_dict.get_cached_dict()
    
    assert cached == {'speed': 50, 'distance': 25.5, 'name': 'vehicle'}


def test_get_cached_dict_with_no_accessed_values():
    """Test get_cached_dict returns empty dict when no values accessed."""
    resolvers = {
        'a': lambda: 1,
        'b': lambda: 2,
    }
    lazy_dict = LazyDict(resolvers)
    
    # Don't access any values
    cached = lazy_dict.get_cached_dict()
    
    # Should be an empty dict
    assert cached == {}
    assert isinstance(cached, dict)

