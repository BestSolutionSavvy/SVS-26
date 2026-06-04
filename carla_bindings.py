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

    def get_cached_dict(self) -> dict:
        """Ritorna un dict normale con tutte le variabili già calcolate."""
        return dict(self)


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
        """
        Returns True if ego has right of way:
        - False if ego is facing a stop sign or red traffic light ahead
        - True if no vehicles on the right
        - True if vehicles on the right are constrained by stop signs or red lights
        - False if vehicles on the right have no constraints
        """
        ego_loc = self.get_ego_location()
        ego_tf = self.ego_vehicle.get_transform()
        ego_fwd = ego_tf.get_forward_vector()
        
        try:
            stop_signs = list(self.world.get_actors().filter("traffic.stop"))
            traffic_lights = list(self.world.get_actors().filter("traffic.traffic_light"))
        except:
            stop_signs = []
            traffic_lights = []
        
        # Check if ego has a stop sign ahead
        for sign in stop_signs:
            sign_loc = sign.get_location()
            rel_to_sign = sign_loc - ego_loc
            fwd_to_sign = rel_to_sign.x * ego_fwd.x + rel_to_sign.y * ego_fwd.y
            
            if 0 < fwd_to_sign < 30.0:
                return False
        
        # Check if ego has a red traffic light ahead
        for light in traffic_lights:
            light_loc = light.get_location()
            rel_to_light = light_loc - ego_loc
            fwd_to_light = rel_to_light.x * ego_fwd.x + rel_to_light.y * ego_fwd.y
            
            if 0 < fwd_to_light < 30.0:
                state = light.get_state()
                if state == carla.TrafficLightState.Red:
                    return False
        
        # Ego has right of way if no vehicles on the right
        if not self.is_vehicle_on_right(narrow=False):
            return True
        
        # Vehicles on the right: ego has right of way if they're constrained by stop signs/red lights
        if self._right_vehicles_constrained():
            return True
        
        # Vehicles on the right without constraints -> ego doesn't have right of way
        return False

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

    def _right_vehicles_constrained(self) -> bool:
        """Returns True if vehicles on the right have a stop sign or red traffic light ahead."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        right_vec = ego_tf.get_right_vector()

        fwd_range = 30.0
        right_range = 3.0

        try:
            current_vehicles = list(self.world.get_actors().filter("vehicle.*"))
            stop_signs = list(self.world.get_actors().filter("traffic.stop"))
            traffic_lights = list(self.world.get_actors().filter("traffic.traffic_light"))
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
                        # Found a vehicle on the right, check if it has stop/red light ahead
                        v_tf = v.get_transform()
                        v_fwd = v_tf.get_forward_vector()
                        v_loc = v_tf.location

                        # Check stop signs
                        for sign in stop_signs:
                            sign_loc = sign.get_location()
                            rel_to_sign = sign_loc - v_loc
                            fwd_to_sign = rel_to_sign.x * v_fwd.x + rel_to_sign.y * v_fwd.y
                            
                            if 0 < fwd_to_sign < 30.0:
                                return True

                        # Check traffic lights (red)
                        for light in traffic_lights:
                            light_loc = light.get_location()
                            rel_to_light = light_loc - v_loc
                            fwd_to_light = rel_to_light.x * v_fwd.x + rel_to_light.y * v_fwd.y
                            
                            if 0 < fwd_to_light < 30.0:
                                state = light.get_state()
                                if state == carla.TrafficLightState.Red:
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
            'threshold_safe': max(1, ego_speed * 0.5  * multiplier),
            'threshold_min':  max(1, ego_speed * 0.25 * multiplier),
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