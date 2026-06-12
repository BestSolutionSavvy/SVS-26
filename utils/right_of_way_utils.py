import carla
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ZoneConfig:
    """
    Configuration parameters for the proximity detection zones.

    Defines rectangular areas in the ego vehicle's local frame 
    (Forward = +X, Right = +Y).
    """
    forward_offset: float = 0.0
    lateral_offset: float = 0.5
    length: float = 25.0
    width: float = 6.0
    check_z_range: float = 2.0


def _world_to_local(
    ego_transform: carla.Transform,
    actor_location: carla.Location
) -> Tuple[float, float, float]:
    """
    Transform a world location into the local coordinate frame of the ego vehicle.

    Parameters
    ----------
    ego_transform : carla.Transform
        The current global transform of the ego vehicle.
    actor_location : carla.Location
        The global location of the target actor.

    Returns
    -------
    Tuple[float, float, float]
        A tuple containing (local_x, local_y, local_z), where +X is forward 
        and +Y is right relative to the ego vehicle.
    """
    dx = actor_location.x - ego_transform.location.x
    dy = actor_location.y - ego_transform.location.y
    dz = actor_location.z - ego_transform.location.z

    yaw_rad = math.radians(ego_transform.rotation.yaw)
    cos_yaw = math.cos(yaw_rad)
    sin_yaw = math.sin(yaw_rad)

    local_x = cos_yaw * dx + sin_yaw * dy
    local_y = -sin_yaw * dx + cos_yaw * dy

    return local_x, local_y, dz


def _point_in_rect(
    local_x: float,
    local_y: float,
    forward_offset: float,
    lateral_offset: float,
    length: float,
    width: float,
) -> bool:
    """
    Check if a 2D point lies within a specific rectangular zone in the local frame.

    Parameters
    ----------
    local_x : float
        Target X coordinate (forward).
    local_y : float
        Target Y coordinate (right).
    forward_offset : float
        Start distance of the zone along the X axis.
    lateral_offset : float
        Start distance of the zone along the Y axis.
    length : float
        Total length of the zone along the X axis.
    width : float
        Total width of the zone along the Y axis.

    Returns
    -------
    bool
        True if the point is inside the rectangle boundaries, False otherwise.
    """
    in_x = forward_offset <= local_x <= forward_offset + length
    in_y = lateral_offset <= local_y <= lateral_offset + width
    return in_x and in_y


def check_right_forward_zones(
    ego_vehicle: carla.Actor,
    world: carla.World,
    far_config: ZoneConfig = ZoneConfig(
        forward_offset=0.0,
        lateral_offset=0.0,
        length=30.0,
        width=10.0,
        check_z_range=2.0
    ),
    near_config: ZoneConfig = ZoneConfig(
        forward_offset=0.0,
        lateral_offset=0.0,
        length=15.0,
        width=5.0,
        check_z_range=2.0
    ),
) -> Dict[str, List[carla.Actor]]:
    """
    Evaluate surrounding vehicles to detect proximity threats in designated zones.

    Scans all active vehicles in the CARLA world, filters out the ego vehicle and 
    objects outside the vertical range, and maps them to either to the far or 
    near zone based on their relative coordinates.

    Parameters
    ----------
    ego_vehicle : carla.Actor
        The reference vehicle executing the checks.
    world : carla.World
        The current CARLA world instance.
    config : ZoneConfig, optional
        Custom dimensions for the zones. Defaults to None, which initializes 
        default ZoneConfig values.

    Returns
    -------
    Dict[str, List[carla.Actor]]
        A dictionary mapping zone names to lists of vehicles detected within each zone.
    """
    ego_transform = ego_vehicle.get_transform()
    ego_id = ego_vehicle.id

    all_vehicles: List[carla.Actor] = [
        a for a in world.get_actors().filter("vehicle.*")
        if a.id != ego_id
    ]

    far_vehicles: List[carla.Actor] = []
    near_vehicles: List[carla.Actor] = []

    for vehicle in all_vehicles:
        actor_loc = vehicle.get_location()
        lx, ly, lz = _world_to_local(ego_transform, actor_loc)
        in_far = False
        in_near = False

        if abs(lz) <= far_config.check_z_range:
            in_far = _point_in_rect(
                lx, ly,
                far_config.forward_offset,
                far_config.lateral_offset,
                far_config.length,
                far_config.width,
            )
        
        if abs(lz) <= near_config.check_z_range:
            in_near = _point_in_rect(
                lx, ly,
                near_config.forward_offset,
                near_config.lateral_offset,
                near_config.length,
                near_config.width,
            )
        
        if in_far:
            far_vehicles.append(vehicle)
        if in_near:
            near_vehicles.append(vehicle)
            
    return {
        "far_zone": far_vehicles,
        "near_zone": near_vehicles
    }
