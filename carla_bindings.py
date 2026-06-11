import carla
from typing import Dict, Optional
from utils.lazy_dict import LazyDict
from utils.right_of_way_utils import ZoneConfig, check_right_forward_zones, ProximityStatus


class DataBinder:
    """Binds guard variables to CARLA world queries."""

    def __init__(self, world: carla.World, ego_vehicle: carla.Actor):
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.map_obj = world.get_map()

        self._vehicle_ahead = None
        self._wedge_vehicle = None
        self._sign_ahead = None
        self._last_traffic_light = None

    def get_ego_speed(self) -> float:
        vel = self.ego_vehicle.get_velocity()
        return (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5

    def get_ego_location(self) -> carla.Location:
        return self.ego_vehicle.get_transform().location

    def get_ego_forward_vector(self) -> carla.Vector3D:
        return self.ego_vehicle.get_transform().get_forward_vector()

    def _vehicle_endpoints(self, vehicle: carla.Actor):
        """Return (front, back, forward_vector, location) for a vehicle."""
        tf = vehicle.get_transform()
        loc = tf.location
        fwd = tf.get_forward_vector()
        bbox = vehicle.bounding_box
        front = loc + carla.Location(
            x=fwd.x * bbox.extent.x,
            y=fwd.y * bbox.extent.x,
            z=0,
        )
        back = loc - carla.Location(
            x=fwd.x * bbox.extent.x,
            y=fwd.y * bbox.extent.x,
            z=0,
        )
        return front, back, fwd, loc

    def _safe_get_waypoint(self, loc: carla.Location):
        """Wrapper around map_obj.get_waypoint that returns None on failure."""
        try:
            return self.map_obj.get_waypoint(loc, project_to_road=True)
        except:
            return None

    def _lane_edge_info(self, vehicle: carla.Actor):
        """Compute lane-edge distances and related info for a vehicle.

        Returns None if waypoint lookup fails or we're in a junction.
        """
        waypoint = self._safe_get_waypoint(vehicle.get_transform().location)
        if waypoint is None or waypoint.is_junction:
            return None
        rel_vec = vehicle.get_transform().location - waypoint.transform.location
        right_vec = waypoint.transform.get_right_vector()
        signed_offset = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
        half_lane = waypoint.lane_width / 2.0
        half_car = vehicle.bounding_box.extent.y
        right_edge_dist = half_lane - (signed_offset + half_car)
        left_edge_dist = half_lane - (-signed_offset + half_car)
        min_dist = min(right_edge_dist, left_edge_dist)
        return {
            'waypoint': waypoint,
            'signed_offset': signed_offset,
            'half_lane': half_lane,
            'half_car': half_car,
            'right_edge_dist': right_edge_dist,
            'left_edge_dist': left_edge_dist,
            'min_dist': min_dist,
        }
    def get_ego_distance_to_sign(self, sign_type: str = "stop") -> float:
        return self._get_distance_to_sign(self.ego_vehicle, sign_type=sign_type)

    def get_ego_distance_to_lead(self) -> float:
        """
        Distance from ego front bumper to lead vehicle rear bumper

        Returns
        -------
        float
            Distance in meters, or inf if no lead vehicle detected.
        """
        ego_front, ego_back, ego_fwd, ego_loc = self._vehicle_endpoints(self.ego_vehicle)
        ego_waypoint = self._safe_get_waypoint(ego_loc)
        ego_lane_id = ego_waypoint.lane_id if ego_waypoint is not None else None
        min_dist = float('inf')
        best_vehicle = None
        current_vehicles = list(self.world.get_actors().filter("vehicle.*"))
        for v in current_vehicles:
            if v.id == self.ego_vehicle.id:
                continue
            v_loc = v.get_transform().location
            rel_vec = v_loc - ego_loc
            dot = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y
            if dot < 0:
                continue
            v_waypoint = self._safe_get_waypoint(v_loc)
            if ego_lane_id is not None and (v_waypoint is None or abs(v_waypoint.lane_id - ego_lane_id) > 1):
                continue
            _, v_back, _, _ = self._vehicle_endpoints(v)
            dist = ego_front.distance(v_back)
            if dist < min_dist:
                min_dist = dist
                best_vehicle = v
        self._vehicle_ahead = best_vehicle
        return min_dist

    def get_ego_min_line_distance(self) -> float:
        """
        Minimum lateral distance from the ego bounding box edge to the nearest lane line.

        Returns
        -------
        float
            - -1.0 if an edge has crossed a line (violation sentinel).
            - inf if inside a junction or on API failure.
        """
        info = self._lane_edge_info(self.ego_vehicle)
        if info is None:
            return float('inf')
        return -1.0 if info['min_dist'] < 0.0 else info['min_dist']

    def ego_is_in_intersection(self) -> bool:
        return self._is_in_intersection(self.ego_vehicle)

    def ego_can_enter_intersection(self) -> bool:
        return self._can_enter_intersection(self.ego_vehicle)

    def other_can_enter_intersection(self) -> bool:
        """
        checks if the vehicle detected in the right wedge can enter the intersection.
        used as a secondary condition for right_of_way violation, to avoid flagging vehicles 
        that are waiting at a red light or stop sign.
        """
        if self._wedge_vehicle is not None:
            return (not self.vehicle_has_stop_sign(self._wedge_vehicle) and self._can_enter_intersection(self._wedge_vehicle)) or self._is_in_intersection(self._wedge_vehicle)
        return False

    def get_lane_marking_type(self) -> str:
        """
        Returns
        -------
        str
            - 'continuous' if the closest lane marking is solid
            - 'dashed' if broken
            - else 'unknown'.
        """
        info = self._lane_edge_info(self.ego_vehicle)
        if info is None:
            return 'unknown'
        waypoint = info['waypoint']
        # Determine which marking is closer
        if abs(info['right_edge_dist']) <= abs(info['left_edge_dist']):
            marking_type = waypoint.right_lane_marking.type
        else:
            marking_type = waypoint.left_lane_marking.type

        if marking_type == carla.LaneMarkingType.Solid:
            return 'continuous'
        elif marking_type in (carla.LaneMarkingType.Broken,
                              carla.LaneMarkingType.BrokenSolid,
                              carla.LaneMarkingType.SolidBroken,
                              carla.LaneMarkingType.BrokenBroken):
            return 'dashed'
        else:
            return 'unknown'

    def get_indicator_state(self) -> Optional[str]:
        """
        Returns
        -------
        Optional[str]
            - 'left' if left blinker on
            - 'right' if right blinker on
            - 'both' if hazard lights on
            - None if no indicators on
        """
        lights = self.ego_vehicle.get_light_state()
        if lights & carla.VehicleLightState.LeftBlinker:
            return 'left'
        elif lights & carla.VehicleLightState.RightBlinker:
            return 'right'
        elif lights & carla.VehicleLightState.All:
            return 'both'
        return None

    def get_steering_direction(self) -> str:
        """
        Returns
        -------
        str
            - 'left' if steering angle negative
            - 'right' if steering angle positive
        """
        control = self.ego_vehicle.get_control()
        return 'left' if control.steer < 0 else 'right'

    def vehicle_has_stop_sign(self, vehicle: carla.Actor) -> bool:
        """
        Returns
        -------
        bool
            True if there is a stop sign ahead of the vehicle, strictly in the vehicle's lane in 30m range.
        """
        return 0 < self._get_distance_to_sign(vehicle, sign_type="stop") < 30.0

    def vehicle_has_red_light(self, vehicle: carla.Actor) -> bool:
        """
        Returns
        -------
        bool
            True if there is a red traffic light ahead of the vehicle, strictly in the vehicle's lane.
        """
        if not vehicle.is_at_traffic_light():
            return True
        if vehicle.get_traffic_light_state() == carla.TrafficLightState.Red:
            return True
        return False

    def _get_ego_wedge_state(self):
        """
        Used to check if the right wedge of the ego vehicle is occupied by another vehicle, 
        and if so whether it's a warning or violation based on proximity.
        The wedge is defined as a rectangle extending forward and to the right of the ego vehicle, 
        with configurable dimensions. A violation is flagged if another vehicle is detected 
        within the near zone, and a warning if detected in the far zone but not the near zone.

        Returns
        -------
        ZoneCheckResult
            Contains the status (CLEAR, WARNING, VIOLATION) and lists of vehicles in each zone.
        """
        config = ZoneConfig(
            warn_forward_offset=0.0,
            warn_lateral_offset=0.5,
            warn_length=25.0,
            warn_width=6.0,
            viol_forward_offset=0.0,
            viol_lateral_offset=0.5,
            viol_length=12.0,
            viol_width=3.0,
        )
        return check_right_forward_zones(self.ego_vehicle, self.world, config)

    def _calculate_safe_distance(self) -> Dict[str, float]:
        """
        Calculates the safe distance thresholds for the ego vehicle based on its current speed and weather conditions.

        Returns
        -------
        Dict[str, float]
            A dictionary containing:
            - 'threshold_safe': the distance at which the ego should consider itself at a safe following distance.
            - 'threshold_min': the minimum distance before a safety violation is flagged.
        """
        ego_speed = self.get_ego_speed()
        weather = self.world.get_weather()
        multiplier = 1.3 if (
            weather.precipitation > 0 or
            weather.fog_density > 0 or
            weather.sun_altitude_angle < 0
        ) else 1.0
        return {
            'threshold_safe': max(1, ego_speed * 0.5 * multiplier),
            'threshold_min':  max(1, ego_speed * 0.25 * multiplier),
        }

    def _get_distance_to_sign(self, vehicle: carla.Actor, sign_type: str = "stop") -> float:
        """
        Signed distance from the front bumper to the nearest same-lane sign.

        Parameters
        -------
        vehicle: carla.Actor
            The vehicle for which to check the sign distance
        sign_type: str
            "stop" or the suffix of other sign types

        Returns
        -------
        float
            positive distance if the sign is ahead, negative if behind, inf if none
        """
        front, _back, fwd, loc = self._vehicle_endpoints(vehicle)
        try:
            if sign_type == "stop":
                signs = list(self.world.get_actors().filter("traffic.stop"))
            else:
                signs = list(self.world.get_actors().filter(
                    f"traffic.{sign_type}"))
        except:
            return float('inf')
        waypoint = self._safe_get_waypoint(loc)
        lane_id = waypoint.lane_id if waypoint is not None else None
        min_signed_dist = float('inf')
        best_sign = None
        for sign in signs:
            sign_loc = sign.get_location()
            rel_vec = sign_loc - front
            fwd_proj = rel_vec.x * fwd.x + rel_vec.y * fwd.y
            if fwd_proj < -5.0:
                continue
            try:
                sign_waypoint = self.map_obj.get_waypoint(
                    sign_loc, project_to_road=True)
                if lane_id is not None and sign_waypoint.lane_id != lane_id:
                    continue
            except:
                pass
            distance = front.distance(sign_loc)
            signed_dist = distance if fwd_proj >= 0 else -distance
            if abs(signed_dist) < abs(min_signed_dist):
                min_signed_dist = signed_dist
                best_sign = sign
        self._sign_ahead = best_sign
        return min_signed_dist

    def _is_in_intersection(self, vehicle: carla.Actor) -> bool:
        vehicle_loc = vehicle.get_transform().location
        try:
            waypoint = self.map_obj.get_waypoint(
                vehicle_loc, project_to_road=True)
            return waypoint.is_intersection
        except:
            return False

    def _can_enter_intersection(self, vehicle: carla.Actor) -> bool:
        """checks if the given vehicle can enter the intersection: no red light"""
        return not self.vehicle_has_red_light(vehicle)

    def compute_scene_data(self) -> LazyDict:
        """
        Returns
        -------
        LazyDict
            A dictionary-like object where values are computed on demand via bound methods.
        """
        lane_marking_cache = {}
        safe_thresh_cache = {}

        def lane_marking():
            if not lane_marking_cache:
                lane_marking_cache['v'] = self.get_lane_marking_type()
            return lane_marking_cache['v']

        def safe_thresh():
            if not safe_thresh_cache:
                safe_thresh_cache['v'] = self._calculate_safe_distance()
            return safe_thresh_cache['v']
        right_zone_cache = {}

        def right_zone():
            if not right_zone_cache:
                right_zone_cache['v'] = self._get_ego_wedge_state()
                if right_zone_cache['v'].status == ProximityStatus.VIOLATION:
                    self._wedge_vehicle = right_zone_cache['v'].violation_vehicles[0]
                elif right_zone_cache['v'].status == ProximityStatus.WARNING:
                    self._wedge_vehicle = right_zone_cache['v'].warning_vehicles[0]
                else:
                    self._wedge_vehicle = None
            return right_zone_cache['v']

        resolvers = {
            'ego_speed': self.get_ego_speed,
            'ego_location': self.get_ego_location,
            'distance_to_sign': self.get_ego_distance_to_sign,
            'distance_to_lead': self.get_ego_distance_to_lead,
            'safe_distance': lambda: safe_thresh()['threshold_safe'],
            'min_distance': lambda: safe_thresh()['threshold_min'],
            'in_intersection': self.ego_is_in_intersection,
            'ego_can_enter_intersection': self.ego_can_enter_intersection,
            'other_can_enter_intersection': self.other_can_enter_intersection,
            'right_wedge_far': lambda: right_zone().status != ProximityStatus.CLEAR,
            'right_wedge_near': lambda: len(right_zone().violation_vehicles) > 0,
            'min_line_distance': self.get_ego_min_line_distance,
            'line_continuous': lambda: lane_marking() == 'continuous',
            'line_dashed': lambda: lane_marking() == 'dashed',
            'indicator': self.get_indicator_state,
            'direction': self.get_steering_direction,
        }
        return LazyDict(resolvers)
