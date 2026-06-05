"""Quick placement scenarios for rule testing.

Each function receives the ego vehicle (a CARLA actor) and places it
at a specific map location under defined conditions. Functions
return a dict with keys: `ego`, `transform`, `others`.
"""
from typing import Any, Dict, List

import random
import carla
from utils.carla_utils import spawn_vehicle_ahead, spawn_random_vehicle_no_bike_at


def lane_keeping_scenario(ego_vehicle: carla.Actor) -> Dict[str, Any]:
    """Align `ego_vehicle` to the center of its lane.

        Parameters:
        - ego_vehicle: CARLA actor representing the ego vehicle.

        Returns:
        - Dict[str, Any]: dict with keys:
            - `ego`: the passed actor
            - `transform`: the `carla.Transform` used to position it
            - `others`: empty list (no other actors created)
    """
    world = ego_vehicle.get_world()
    ego_tf = ego_vehicle.get_transform()
    wp = world.get_map().get_waypoint(
        ego_tf.location, project_to_road=True, lane_type=carla.LaneType.Driving
    )
    loc = carla.Location(wp.transform.location.x,
                         wp.transform.location.y, wp.transform.location.z + 0.3)
    tf = carla.Transform(loc, wp.transform.rotation)
    ego_vehicle.set_transform(tf)
    try:
        ego_vehicle.set_autopilot(False)
    except Exception:
        pass
    return {"ego": ego_vehicle, "transform": tf, "others": []}


def stop_scenario(ego_vehicle: carla.Actor) -> Dict[str, Any]:
    """Place `ego_vehicle` a few meters before a stop point and stop it.

    Behavior:
    - find the waypoint ~10m ahead (if possible)
    - position `ego` 2m before that waypoint
    - apply `brake=1.0` to stop it
    Returns:
    - Dict[str, Any]: dict with keys `ego`, `transform`, `others`.

    """
    world = ego_vehicle.get_world()
    ego_tf = ego_vehicle.get_transform()
    wp = world.get_map().get_waypoint(
        ego_tf.location, project_to_road=True, lane_type=carla.LaneType.Driving
    )
    try:
        next_wp = wp.next(10.0)[0]
    except Exception:
        next_wp = wp

    stop_loc = next_wp.transform.location - \
        next_wp.transform.get_forward_vector() * 2.0
    tf = carla.Transform(carla.Location(
        stop_loc.x, stop_loc.y, stop_loc.z + 0.3), next_wp.transform.rotation)
    ego_vehicle.set_transform(tf)
    try:
        ego_vehicle.apply_control(
            carla.VehicleControl(throttle=0.0, brake=1.0))
    except Exception:
        pass
    try:
        ego_vehicle.set_autopilot(False)
    except Exception:
        pass
    return {"ego": ego_vehicle, "transform": tf, "others": []}


def right_of_way_scenario(ego_vehicle: carla.Actor) -> Dict[str, Any]:
    """Place ego_vehicle and two other vehicles in fixed right-of-way positions
    in an intersection.

    Fixed positions:
    
    ego:   Location(x=-5.535913, y=119.039459, z=0.001677)
    right: Location(x=-21.044353, y=138.250305, z=0.001681)
    front: Location(x=2.210113, y=147.035950, z=0.001720)

        All spawned vehicles have autopilot disabled.

        Returns:
        
    Dict[str, Any]: dict with keys ego, transform, others."""
    world = ego_vehicle.get_world()

    ego_tf_new = carla.Transform(
        carla.Location(x=-5.535913, y=119.039459, z=0.001677),
        ego_vehicle.get_transform().rotation,
    )
    ego_vehicle.set_transform(ego_tf_new)
    try:
        ego_vehicle.set_autopilot(False)
    except Exception:
        pass

    spawn_points = [
        carla.Transform(
            carla.Location(x=-21.044353, y=138.250305, z=0.001681),
            ego_tf_new.rotation,
        ),
        carla.Transform(
            carla.Location(x=2.210113, y=147.035950, z=0.001720),
            ego_tf_new.rotation,
        ),
    ]

    others: List[carla.Actor] = []
    try:
        for tf in spawn_points:
            other = spawn_random_vehicle_no_bike_at(world, tf, autopilot=False)
            others.append(other)
    except Exception:
        pass

    return {"ego": ego_vehicle, "transform": ego_tf_new, "others": others}

def safe_distance_scenario(ego_vehicle: carla.Actor) -> Dict[str, Any]:
    """Align `ego_vehicle` to the lane and spawn a vehicle shortly ahead.

    Default distance: 8 meters.

    Returns:
    - Dict[str, Any]: dict with keys `ego`, `transform`, `others`.
    """
    world = ego_vehicle.get_world()
    base = lane_keeping_scenario(ego_vehicle)
    others: List[carla.Actor] = []
    try:
        other = spawn_vehicle_ahead(world, ego_vehicle, distances=(8.0,))
        if other is not None:
            try:
                other.set_autopilot(True)
            except Exception:
                pass
            others.append(other)
    except Exception:
        pass

    return {"ego": ego_vehicle, "transform": base.get("transform"), "others": others}
