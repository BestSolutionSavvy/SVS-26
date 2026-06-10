"""Test cases for CARLA bindings."""
from carla_bindings import DataBinder, LazyDict


class DummyVector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class DummyLocation(DummyVector):
    def __add__(self, other):
        return DummyLocation(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return DummyLocation(self.x - other.x, self.y - other.y, self.z - other.z)

    def distance(self, other):
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5


class DummyExtent:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class DummyBoundingBox:
    def __init__(self, extent_x, extent_y):
        self.extent = DummyExtent(extent_x, extent_y)


class DummyTransform:
    def __init__(self, location, forward, right):
        self.location = location
        self._forward = forward
        self._right = right

    def get_forward_vector(self):
        return self._forward

    def get_right_vector(self):
        return self._right


class DummyActor:
    def __init__(self, actor_id, location, forward, right, extent_x=2.0, extent_y=1.0):
        self.id = actor_id
        self.bounding_box = DummyBoundingBox(extent_x, extent_y)
        self._transform = DummyTransform(location, forward, right)

    def get_transform(self):
        return self._transform


class DummyActorList:
    def __init__(self, vehicles):
        self._vehicles = vehicles

    def filter(self, pattern):
        if pattern == "vehicle.*":
            return list(self._vehicles)
        return []


class DummyMap:
    def get_waypoint(self, location, project_to_road=True):
        return None


class DummyWorld:
    def __init__(self, vehicles):
        self._actors = DummyActorList(vehicles)

    def get_map(self):
        return DummyMap()

    def get_actors(self):
        return self._actors


def build_binder(vehicles):
    ego = DummyActor(
        actor_id=1,
        location=DummyLocation(0.0, 0.0, 0.0),
        forward=DummyVector(1.0, 0.0, 0.0),
        right=DummyVector(0.0, 1.0, 0.0),
        extent_x=2.0,
        extent_y=1.0,
    )
    world = DummyWorld([ego, *vehicles])
    return DataBinder(world, ego)


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




