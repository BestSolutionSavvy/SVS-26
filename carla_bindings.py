import carla
from typing import Dict, Any, Optional
from collections import deque


class LazyDict(dict):
    def __init__(self, resolvers: dict):
        super().__init__()
        self._resolvers = resolvers

    def __missing__(self, key):
        if key not in self._resolvers:
            raise KeyError(key)
        resolver = self._resolvers[key]
        # If it's callable, call it; otherwise use the value directly
        value = resolver() if callable(resolver) else resolver
        self[key] = value
        return value


class DataBinder:
    """Binds guard variables to CARLA world queries."""

    def __init__(self, world: carla.World, ego_vehicle: carla.Actor):
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.map_obj = world.get_map()          # cached: never changes at runtime
        self.all_vehicles = list(world.get_actors().filter(
            "vehicle.*"))  # cached: spawned once
        self.stop_signs = list(world.get_actors().filter("traffic.stop"))

        self._vehicle_ahead = None
        self._sign_ahead = None
        self._last_lateral_offset = 0.0
        self._offset_history = deque(maxlen=30)  # Rolling window of last 30 lateral offsets

    # --- Dynamic variables ---

    def get_ego_speed(self) -> float:
        vel = self.ego_vehicle.get_velocity()
        return (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5

    def get_ego_location(self) -> carla.Location:
        return self.ego_vehicle.get_transform().location

    def get_ego_forward_vector(self) -> carla.Vector3D:
        return self.ego_vehicle.get_transform().get_forward_vector()

    def get_distance_to_sign(self, sign_type: str = "stop") -> float:
        """Distance to the nearest sign ahead on the same lane.

        Returns:
            - Positive: sign is ahead of ego (before waypoint)
            - Negative: sign is behind ego (already crossed)
            - inf: no sign found on the ego's direction/lane
        """
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()

        signs = self.stop_signs if sign_type == "stop" else list(
            self.world.get_actors().filter(f"traffic.{sign_type}"))

        # Get ego's current lane
        try:
            ego_waypoint = self.map_obj.get_waypoint(
                ego_loc, project_to_road=True)
            ego_lane_id = ego_waypoint.lane_id
        except:
            ego_lane_id = None

        min_signed_dist = float('inf')
        best_sign = None

        for sign in signs:
            sign_loc = sign.get_location()
            rel_vec = sign_loc - ego_loc

            # Dot product to check if sign is ahead (positive) or behind (negative)
            dot_product = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y

            # Only consider signs that are somewhat ahead (dot >= -5.0 to catch signs we just passed)
            if dot_product < -5.0:
                continue

            # Check if sign is on the same lane (heading-wise)
            try:
                sign_waypoint = self.map_obj.get_waypoint(
                    sign_loc, project_to_road=True)
                # Only consider signs on the same lane_id
                if ego_lane_id is not None and sign_waypoint.lane_id != ego_lane_id:
                    continue
            except:
                pass

            # Calculate signed distance: positive ahead, negative behind
            distance = ego_loc.distance(sign_loc)
            signed_dist = distance if dot_product >= 0 else -distance

            # Keep the closest (most relevant) sign
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

        # Ego front bumper location
        ego_bbox = self.ego_vehicle.bounding_box
        ego_front = ego_loc + carla.Location(
            x=ego_fwd.x * ego_bbox.extent.x,
            y=ego_fwd.y * ego_bbox.extent.x,
            z=0  # Keep z at center level
        )

        try:
            ego_waypoint = self.map_obj.get_waypoint(
                ego_loc, project_to_road=True)
            ego_lane_id = ego_waypoint.lane_id
        except:
            ego_lane_id = None

        min_dist = float('inf')
        best_vehicle = None

        # Refresh vehicle list from world (don't use cached list)
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
                v_waypoint = self.map_obj.get_waypoint(
                    v_loc, project_to_road=True)
                v_lane_id = v_waypoint.lane_id

                if ego_lane_id is not None and abs(v_lane_id - ego_lane_id) > 1:
                    continue
            except:
                continue

            # Vehicle rear bumper location
            v_tf = v.get_transform()
            v_fwd = v_tf.get_forward_vector()
            v_bbox = v.bounding_box
            v_back = v_loc - carla.Location(
                x=v_fwd.x * v_bbox.extent.x,
                y=v_fwd.y * v_bbox.extent.x,
                z=0  # Keep z at center level
            )

            dist = ego_front.distance(v_back)
            if dist < min_dist:
                min_dist = dist
                best_vehicle = v

        self._vehicle_ahead = best_vehicle
        return min_dist

    def get_abs_lane_deviation(self) -> float:
        """Lateral distance from lane center."""
        ego_loc = self.get_ego_location()
        try:
            waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            rel_vec = ego_loc - waypoint.transform.location
            right_vec = waypoint.transform.get_right_vector()
            return abs(rel_vec.x * right_vec.x + rel_vec.y * right_vec.y)
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
            
            # Solid types = continuous line
            if marking_type == carla.LaneMarkingType.Solid:
                return 'continuous'
            # Broken and mixed types = dashed line
            elif marking_type in (carla.LaneMarkingType.Broken, 
                                 carla.LaneMarkingType.BrokenSolid,
                                 carla.LaneMarkingType.SolidBroken,
                                 carla.LaneMarkingType.BrokenBroken):
                return 'dashed'
            # If right marking is unavailable, try left marking
            elif marking_type == carla.LaneMarkingType.NONE:
                left_marking = waypoint.left_lane_marking.type
                if left_marking == carla.LaneMarkingType.Solid:
                    return 'continuous'
                elif left_marking in (carla.LaneMarkingType.Broken,
                                     carla.LaneMarkingType.BrokenSolid,
                                     carla.LaneMarkingType.SolidBroken,
                                     carla.LaneMarkingType.BrokenBroken):
                    return 'dashed'
                else:
                    return 'unknown'
            else:
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
        """Returns 'left', 'right', or 'straight'.
        
        ROLLING ACCUMULATION APPROACH:
        - Maintain a rolling window of last 30 lateral offsets
        - Calculate net (accumulated) movement direction
        - If indicator is active, verify movement matches indicator
        - Allows smooth lane changes (oscillations) but catches opposite movements
        """
        indicator = self.get_indicator_state()
        
        ego_loc = self.get_ego_location()
        current_offset = 0.0
        
        try:
            waypoint = self.map_obj.get_waypoint(ego_loc, project_to_road=True)
            rel_vec = ego_loc - waypoint.transform.location
            right_vec = waypoint.transform.get_right_vector()
            current_offset = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
        except:
            pass
        
        # Add current offset to rolling history
        self._offset_history.append(current_offset)
        self._last_lateral_offset = current_offset
        
        # Calculate accumulated (net) movement over rolling window
        accumulated = sum(self._offset_history) if self._offset_history else 0.0
        window_size = len(self._offset_history)
        avg_offset = accumulated / window_size if window_size > 0 else 0.0
        
        # Determine direction from net movement (with hysteresis: 0.05m threshold)
        if abs(avg_offset) > 0.05:
            net_direction = 'left' if avg_offset < 0 else 'right'
        else:
            net_direction = 'straight'
        
        # If indicator is active, verify coherence
        if indicator in ('left', 'right'):
            # Check if net movement matches indicator
            if net_direction != 'straight' and net_direction != indicator:
                # Incoherent: indicator says X but net movement is Y
                return net_direction
            else:
                # Coherent: return the indicator
                return indicator
        
        # No indicator: return net direction from position
        return net_direction

    def has_right_of_way(self) -> bool:
        """Placeholder — always True until rule logic is implemented."""
        return True

    def is_vehicle_on_right(self, narrow: bool = False) -> bool:
        """Check if any vehicle is on the right of the ego path.
        narrow=True uses tighter detection ranges for intersection checks."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        right_vec = ego_tf.get_right_vector()
        fwd_range = 15.0 if narrow else 30.0
        right_range = 1.5 if narrow else 3.0
        for v in self.all_vehicles:
            if v.id == self.ego_vehicle.id:
                continue
            rel_vec = v.get_transform().location - ego_loc
            fwd_dist = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y
            if 0 < fwd_dist < fwd_range:
                right_dist = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
                if 0 < right_dist < right_range:
                    return True
        return False

    def _calculate_safe_thresholds(self) -> Dict[str, float]:
        """Calculate safe distance thresholds dynamically based on speed and weather.
        Uses 2-second rule: distance = velocity * time_factor."""
        ego_speed = self.get_ego_speed()
        weather = self.world.get_weather()

        threshold_safe = ego_speed * 0.5
        threshold_min = ego_speed * 0.25

        weather_multiplier = 1.0
        if weather.precipitation > 0 or weather.fog_density > 0 or weather.sun_altitude_angle < 0:
            weather_multiplier = 1.3

        return {
            'threshold_safe': threshold_safe * weather_multiplier,
            'threshold_min': threshold_min * weather_multiplier,
        }

    # --- Scene data ---

    def compute_scene_data(self) -> LazyDict:
        """Compute all guard variables for the current scene. Uses lazy evaluation and caching."""
        
        lane_marking_cache = {}
        safe_thresh_cache = {}

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
            'threshold_safe': lambda: safe_thresh()['threshold_safe'],
            'threshold_min': lambda: safe_thresh()['threshold_min'],

            # RIGHT_OF_WAY
            'ego_location':          self.get_ego_location,
            'in_intersection':       self.is_in_intersection,
            'precedence':            self.has_right_of_way,
            'broad_right_occupied': lambda: self.is_vehicle_on_right(narrow=False),
            'narrow_right_occupied': lambda: self.is_vehicle_on_right(narrow=True),

            # LANE_KEEPING
            'abs_lane_deviation': self.get_abs_lane_deviation,
            'line_continuous': lambda: self.get_indicator_state() is None and lane_marking() == 'continuous',
            'line_dashed': lambda: lane_marking() == 'dashed',
            'indicator':          self.get_indicator_state,
            'direction':          self.get_steering_direction,
        }
        return LazyDict(resolvers)