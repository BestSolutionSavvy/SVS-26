"""Quick placement scenarios for rule testing.

Each function receives the ego vehicle (a CARLA actor) and places it
at a specific map location under defined conditions. Functions
return a dict with keys: `ego`, `transform`, `others`.
"""
from typing import Any, Dict, List

import random
import carla
from utils.carla_utils import spawn_vehicle_ahead


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
    """Place `ego_vehicle` before an intersection and (if possible) spawn
    another vehicle crossing the intersection to simulate right-of-way.

    The spawned vehicle (if any) will be set to autopilot.

    Returns:
    - Dict[str, Any]: dict with keys `ego`, `transform`, `others`.
    """
    world = ego_vehicle.get_world()
    ego_tf = ego_vehicle.get_transform()
    road_map = world.get_map()
    cur_wp = road_map.get_waypoint(
        ego_tf.location, project_to_road=True, lane_type=carla.LaneType.Driving)

    junction_wp = None
    for d in range(5, 200, 5):
        try:
            cands = cur_wp.next(float(d))
        except Exception:
            cands = []
        for c in cands:
            if c.is_junction:
                junction_wp = c
                break
        if junction_wp:
            break

    if junction_wp is None:
        junction_wp = cur_wp

    before_loc = junction_wp.transform.location - \
        junction_wp.transform.get_forward_vector() * 6.0
    ego_tf_new = carla.Transform(carla.Location(
        before_loc.x, before_loc.y, before_loc.z + 0.3), junction_wp.transform.rotation)
    ego_vehicle.set_transform(ego_tf_new)
    try:
        ego_vehicle.set_autopilot(False)
    except Exception:
        pass

    others: List[carla.Actor] = []
    try:
        bps = world.get_blueprint_library().filter("vehicle.*")
        if bps:
            bp = random.choice(bps)
            other = world.try_spawn_actor(bp, junction_wp.transform)
            if other is not None:
                try:
                    other.set_autopilot(True)
                except Exception:
                    pass
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
