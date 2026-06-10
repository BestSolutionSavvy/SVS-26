import carla
import math
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum


class ProximityStatus(Enum):
    CLEAR = "clear"
    WARNING = "warning"
    VIOLATION = "violation"


@dataclass
class ZoneConfig:
    """
    Configuration parameters for the proximity detection zones.

    Defines rectangular areas in the ego vehicle's local frame 
    (Forward = +X, Right = +Y).
    """
    warn_forward_offset: float = 0.0    
    warn_lateral_offset: float = 0.5    
    warn_length: float = 12.0          
    warn_width: float = 4.0            

    viol_forward_offset: float = 2.0    
    viol_lateral_offset: float = 0.5    
    viol_length: float = 6.0            
    viol_width: float = 2.5            

    check_z_range: float = 2.0          


@dataclass
class ZoneCheckResult:
    status: ProximityStatus
    warning_vehicles: List[carla.Actor]
    violation_vehicles: List[carla.Actor]


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
    config: ZoneConfig = None,
) -> ZoneCheckResult:
    """
    Evaluate surrounding vehicles to detect proximity threats in designated zones.

    Scans all active vehicles in the CARLA world, filters out the ego vehicle and 
    objects outside the vertical range, and maps them to either the warning or 
    violation zone based on their relative coordinates.

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
    ZoneCheckResult
        Object containing the overall security status and lists of vehicles 
        caught inside the warning and violation areas.
    """
    if config is None:
        config = ZoneConfig()

    ego_transform = ego_vehicle.get_transform()
    ego_id = ego_vehicle.id

    all_vehicles: List[carla.Actor] = [
        a for a in world.get_actors().filter("vehicle.*")
        if a.id != ego_id
    ]

    warning_vehicles: List[carla.Actor] = []
    violation_vehicles: List[carla.Actor] = []

    for vehicle in all_vehicles:
        actor_loc = vehicle.get_location()
        lx, ly, lz = _world_to_local(ego_transform, actor_loc)

        if abs(lz) > config.check_z_range:
            continue

        in_violation = _point_in_rect(
            lx, ly,
            config.viol_forward_offset,
            config.viol_lateral_offset,
            config.viol_length,
            config.viol_width,
        )

        in_warning = _point_in_rect(
            lx, ly,
            config.warn_forward_offset,
            config.warn_lateral_offset,
            config.warn_length,
            config.warn_width,
        )

        if in_violation:
            violation_vehicles.append(vehicle)
        elif in_warning:
            warning_vehicles.append(vehicle)

    if violation_vehicles:
        status = ProximityStatus.VIOLATION
    elif warning_vehicles:
        status = ProximityStatus.WARNING
    else:
        status = ProximityStatus.CLEAR

    return ZoneCheckResult(
        status=status,
        warning_vehicles=warning_vehicles,
        violation_vehicles=violation_vehicles,
    )