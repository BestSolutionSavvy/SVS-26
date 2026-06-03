import carla
from typing import Dict, Any, Optional


class LazyDict(dict):
    def __init__(self, resolvers: dict):
        super().__init__()
        self._resolvers = resolvers

    def __missing__(self, key):
        if key not in self._resolvers:
            raise KeyError(key)
        resolver = self._resolvers[key]
        value = resolver() if callable(resolver) else resolver
        self[key] = value
        return value


class DataBinder:
    """Binds guard variables to CARLA world queries."""

    def __init__(self, world: carla.World, ego_vehicle: carla.Actor):
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.map_obj = world.get_map()

        self._vehicle_ahead = None
        self._sign_ahead = None

    # --- Dynamic variables ---

    def get_ego_speed(self) -> float:
        vel = self.ego_vehicle.get_velocity()
        return (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5

    def get_ego_location(self) -> carla.Location:
        return self.ego_vehicle.get_transform().location

    def get_ego_forward_vector(self) -> carla.Vector3D:
        return self.ego_vehicle.get_transform().get_forward_vector()

    def get_distance_to_sign(self, sign_type: str = "stop") -> float:
        """Signed distance from the front bumper to the nearest same-lane sign.

        Returns positive if ahead, negative if already passed, inf if none found.
        Distance is the forward projection (not Euclidean) to handle signs
        placed laterally off the lane centre.
        """
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()

        ego_bbox  = self.ego_vehicle.bounding_box
        ego_front = ego_loc + carla.Location(
            x=ego_fwd.x * ego_bbox.extent.x,
            y=ego_fwd.y * ego_bbox.extent.x,
            z=0,
        )

        try:
            if sign_type == "stop":
                signs = list(self.world.get_actors().filter("traffic.stop"))
            else:
                signs = list(self.world.get_actors().filter(f"traffic.{sign_type}"))
        except:
            return float('inf')

        try:
            ego_waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            ego_lane_id = ego_waypoint.lane_id
        except:
            ego_lane_id = None

        min_signed_dist = float('inf')
        best_sign = None

        for sign in signs:
            sign_loc = sign.get_location()
            rel_vec  = sign_loc - ego_front
            fwd_proj = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y

            if fwd_proj < -5.0:
                continue

            try:
                sign_waypoint = self.map_obj.get_waypoint(sign_loc, project_to_road=True)
                if ego_lane_id is not None and sign_waypoint.lane_id != ego_lane_id:
                    continue
            except:
                pass

            distance    = ego_front.distance(sign_loc)
            signed_dist = distance if fwd_proj >= 0 else -distance

            if abs(signed_dist) < abs(min_signed_dist):
                min_signed_dist = signed_dist
                best_sign = sign

        self._sign_ahead = best_sign
        return min_signed_dist

    def get_distance_to_lead(self) -> float:
        """Distance from ego front bumper to lead vehicle rear bumper. Returns inf if none."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()

        ego_bbox = self.ego_vehicle.bounding_box
        ego_front = ego_loc + carla.Location(
            x=ego_fwd.x * ego_bbox.extent.x,
            y=ego_fwd.y * ego_bbox.extent.x,
            z=0,
        )

        try:
            ego_waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            ego_lane_id = ego_waypoint.lane_id
        except:
            ego_lane_id = None

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

            try:
                v_waypoint = self.map_obj.get_waypoint(v_loc, project_to_road=True)
                if ego_lane_id is not None and abs(v_waypoint.lane_id - ego_lane_id) > 1:
                    continue
            except:
                continue

            v_tf = v.get_transform()
            v_fwd = v_tf.get_forward_vector()
            v_bbox = v.bounding_box
            v_back = v_loc - carla.Location(
                x=v_fwd.x * v_bbox.extent.x,
                y=v_fwd.y * v_bbox.extent.x,
                z=0,
            )

            dist = ego_front.distance(v_back)
            if dist < min_dist:
                min_dist = dist
                best_vehicle = v

        self._vehicle_ahead = best_vehicle
        return min_dist

    def get_min_line_distance(self) -> float:
        """Minimum lateral distance from the ego bounding box edge to the nearest lane line.

        Returns -1.0 if an edge has crossed a line (violation sentinel).
        Returns  0.0 inside junctions or on API failure.
        """
        ego_loc = self.get_ego_location()
        try:
            waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)

            if waypoint.is_junction:
                return 0.0

            rel_vec   = ego_loc - waypoint.transform.location
            right_vec = waypoint.transform.get_right_vector()

            signed_offset = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
            half_lane = waypoint.lane_width / 2.0
            half_car  = self.ego_vehicle.bounding_box.extent.y

            right_edge_dist = half_lane - (signed_offset + half_car)
            left_edge_dist  = half_lane - (-signed_offset + half_car)
            min_dist = min(right_edge_dist, left_edge_dist)

            return -1.0 if min_dist < 0.0 else min_dist
        except:
            return 0.0

    def is_in_intersection(self) -> bool:
        ego_loc = self.get_ego_location()
        try:
            waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            return waypoint.is_intersection
        except:
            return False

    def get_lane_marking_type(self) -> str:
        """Returns 'continuous', 'dashed', or 'unknown'."""
        ego_loc = self.get_ego_location()
        try:
            waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            marking_type = waypoint.right_lane_marking.type

            if marking_type == carla.LaneMarkingType.Solid:
                return 'continuous'
            elif marking_type in (carla.LaneMarkingType.Broken,
                                  carla.LaneMarkingType.BrokenSolid,
                                  carla.LaneMarkingType.SolidBroken,
                                  carla.LaneMarkingType.BrokenBroken):
                return 'dashed'
            elif marking_type == carla.LaneMarkingType.NONE:
                left_marking = waypoint.left_lane_marking.type
                if left_marking == carla.LaneMarkingType.Solid:
                    return 'continuous'
                elif left_marking in (carla.LaneMarkingType.Broken,
                                      carla.LaneMarkingType.BrokenSolid,
                                      carla.LaneMarkingType.SolidBroken,
                                      carla.LaneMarkingType.BrokenBroken):
                    return 'dashed'
            return 'unknown'
        except:
            return 'unknown'

    def get_indicator_state(self) -> Optional[str]:
        """Returns 'left', 'right', 'both', or None."""
        lights = self.ego_vehicle.get_light_state()
        if lights & carla.VehicleLightState.LeftBlinker:
            return 'left'
        elif lights & carla.VehicleLightState.RightBlinker:
            return 'right'
        elif lights & carla.VehicleLightState.All:
            return 'both'
        return None

    def get_steering_direction(self) -> str:
        """Returns 'left' or 'right' based on the steering input."""
        control = self.ego_vehicle.get_control()
        return 'left' if control.steer < 0 else 'right'

    def has_right_of_way(self) -> bool:
        """Returns False if a vehicle is on the right or ego is approaching a stop sign."""
        if self.is_vehicle_on_right(narrow=False):
            return False

        distance_to_stop = self.get_distance_to_sign(sign_type="stop")
        if 0 < distance_to_stop < 30.0 and self.get_ego_speed() > 0.5:
            return False

        return True

    def is_vehicle_on_right(self, narrow: bool = False) -> bool:
        """Returns True if a vehicle is ahead and to the right of the ego."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        right_vec = ego_tf.get_right_vector()

        fwd_range   = 15.0 if narrow else 30.0
        right_range = 1.5  if narrow else 3.0

        try:
            current_vehicles = list(self.world.get_actors().filter("vehicle.*"))
        except:
            return False

        for v in current_vehicles:
            if v.id == self.ego_vehicle.id:
                continue
            try:
                rel_vec  = v.get_transform().location - ego_loc
                fwd_dist = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y
                if 0 < fwd_dist < fwd_range:
                    right_dist = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
                    if 0 < right_dist < right_range:
                        return True
            except:
                continue
        return False

    def _calculate_safe_thresholds(self) -> Dict[str, float]:
        ego_speed = self.get_ego_speed()
        weather   = self.world.get_weather()

        multiplier = 1.3 if (
            weather.precipitation > 0 or
            weather.fog_density > 0 or
            weather.sun_altitude_angle < 0
        ) else 1.0

        return {
            'threshold_safe': ego_speed * 0.5  * multiplier,
            'threshold_min':  ego_speed * 0.25 * multiplier,
        }

    # --- Scene data ---

    def compute_scene_data(self) -> LazyDict:
        """Returns a LazyDict of all guard variables, evaluated on first access."""

        lane_marking_cache = {}
        safe_thresh_cache  = {}

        def lane_marking():
            if not lane_marking_cache:
                lane_marking_cache['v'] = self.get_lane_marking_type()
            return lane_marking_cache['v']

        def safe_thresh():
            if not safe_thresh_cache:
                safe_thresh_cache['v'] = self._calculate_safe_thresholds()
            return safe_thresh_cache['v']

        resolvers = {
            # STOP
            'distance_to_sign': self.get_distance_to_sign,
            'ego_speed':        self.get_ego_speed,

            # SAFE_DISTANCE
            'distance_to_lead': self.get_distance_to_lead,
            'threshold_safe':   lambda: safe_thresh()['threshold_safe'],
            'threshold_min':    lambda: safe_thresh()['threshold_min'],

            # RIGHT_OF_WAY
            'ego_location':          self.get_ego_location,
            'in_intersection':       self.is_in_intersection,
            'precedence':            self.has_right_of_way,
            'broad_right_occupied':  lambda: self.is_vehicle_on_right(narrow=False),
            'narrow_right_occupied': lambda: self.is_vehicle_on_right(narrow=True),

            # LANE_KEEPING
            'min_line_distance': self.get_min_line_distance,
            'line_continuous':   lambda: lane_marking() == 'continuous',
            'line_dashed':       lambda: lane_marking() == 'dashed',
            'indicator':         self.get_indicator_state,
            'direction':         self.get_steering_direction,
        }
        return LazyDict(resolvers)