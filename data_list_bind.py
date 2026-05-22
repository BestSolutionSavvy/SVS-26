import carla
from typing import Dict, Any, Optional, List


class VariableBinder:
    """Binds guard variables to CARLA world queries."""

    def __init__(self, world: carla.World, ego_vehicle: carla.Actor,
                 static_params: Optional[Dict[str, float]] = None):
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.map_obj = world.get_map()          # cached: never changes at runtime
        self.all_vehicles = list(world.get_actors().filter("vehicle.*"))  # cached: spawned once
        self.stop_signs = list(world.get_actors().filter("traffic.stop"))

        self.static_params = static_params or {
            'threshold_safe': 20.0,
            'threshold_min': 10.0,
            'warning_threshold': 0.4,
            'violation_threshold': 0.7,
        }

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
        ego_loc = self.get_ego_location()
        signs = self.stop_signs if sign_type == "stop" else list(self.world.get_actors().filter(f"traffic.{sign_type}"))
        min_dist = float('inf')
        for sign in signs:
            dist = ego_loc.distance(sign.get_location())
            if dist < min_dist:
                min_dist = dist
                self._sign_ahead = sign
        return min_dist

    def get_distance_to_lead(self) -> float:
        """Distance to the nearest vehicle directly ahead. Returns inf if none."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        min_dist = float('inf')
        best_vehicle = None
        for v in self.all_vehicles:
            if v.id == self.ego_vehicle.id:
                continue
            v_loc = v.get_transform().location
            rel_vec = v_loc - ego_loc
            dot = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y
            if dot > 0:
                dist = ego_loc.distance(v_loc)
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
            if waypoint.right_lane_marking.type == carla.LaneMarkingType.Solid:
                return 'continuous'
            elif waypoint.right_lane_marking.type == carla.LaneMarkingType.Dashed:
                return 'dashed'
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
        """Returns 'left', 'right', or 'straight'."""
        steer = self.ego_vehicle.get_control().steer
        if steer < -0.1:
            return 'left'
        elif steer > 0.1:
            return 'right'
        return 'straight'

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
        fwd_range   = 15.0 if narrow else 30.0
        right_range = 1.5  if narrow else 3.0
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

    # --- Static parameters ---

    def get_static_param(self, param_name: str, default: float = 0.0) -> float:
        return self.static_params.get(param_name, default)

    def set_static_param(self, param_name: str, value: float) -> None:
        self.static_params[param_name] = value

    # --- Scene data ---

    def compute_scene_data(self) -> Dict[str, Any]:
        """Compute all guard variables for the current frame.

        No world.get_actors() calls here: vehicles are cached at init.
        No world.get_map() calls here: map is cached at init.
        get_lane_marking_type() is called once and reused for both flags.
        """
        lane_marking = self.get_lane_marking_type()

        return {
            # STOP
            'distance_to_sign': self.get_distance_to_sign(),
            'ego_speed':        self.get_ego_speed(),

            # SAFE_DISTANCE
            'distance_to_lead': self.get_distance_to_lead(),
            'threshold_safe':   self.get_static_param('threshold_safe'),
            'threshold_min':    self.get_static_param('threshold_min'),

            # RIGHT_OF_WAY
            'ego_location':          self.get_ego_location(),
            'in_intersection':       self.is_in_intersection(),
            'precedence':            self.has_right_of_way(),
            'broad_right_occupied':  self.is_vehicle_on_right(narrow=False),
            'narrow_right_occupied': self.is_vehicle_on_right(narrow=True),

            # LANE_KEEPING
            'abs_lane_deviation':  self.get_abs_lane_deviation(),
            'warning_threshold':   self.get_static_param('warning_threshold'),
            'violation_threshold': self.get_static_param('violation_threshold'),
            'line_continuous':     lane_marking == 'continuous',
            'line_dashed':         lane_marking == 'dashed',
            'indicator':           self.get_indicator_state(),
            'direction':           self.get_steering_direction(),
        }

    def __repr__(self) -> str:
        return f"VariableBinder(ego_id={self.ego_vehicle.id}, params={self.static_params})"
