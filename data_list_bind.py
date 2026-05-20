import carla
from typing import Dict, Any, Optional


class VariableBinder:
    """Binds YAML guard variables to CARLA world queries."""
    
    def __init__(self, world: carla.World, ego_vehicle: carla.Actor, 
                 static_params: Optional[Dict[str, float]] = None):
        """Initialize binder with world, ego vehicle, and static parameters."""
        self.world = world
        self.ego_vehicle = ego_vehicle
        
        self.static_params = static_params or {
            'threshold_safe': 20.0,
            'threshold_min': 10.0,
            'warning_threshold': 0.4,
            'violation_threshold': 0.7,
        }
        
        self._vehicle_ahead = None
        self._sign_ahead = None
    
    # Dynamic variables (computed per frame)
    
    def get_ego_speed(self) -> float:
        """Get ego vehicle speed in m/s."""
        vel = self.ego_vehicle.get_velocity()
        return (vel.x**2 + vel.y**2 + vel.z**2) ** 0.5
    
    def get_ego_location(self) -> carla.Location:
        """Get ego vehicle location."""
        return self.ego_vehicle.get_transform().location
    
    def get_ego_forward_vector(self) -> carla.Vector3D:
        """Get ego vehicle forward direction."""
        return self.ego_vehicle.get_transform().get_forward_vector()
    
    def get_distance_to_sign(self, sign_type: str = "stop") -> float:
        """Get distance to nearest traffic sign. Returns inf if not found."""
        ego_loc = self.get_ego_location()
        signs = self.world.get_actors().filter(f"traffic.{sign_type}")
        
        min_dist = float('inf')
        for sign in signs:
            sign_loc = sign.get_location()
            dist = ego_loc.distance(sign_loc)
            if dist < min_dist:
                min_dist = dist
                self._sign_ahead = sign
        
        return min_dist
    
    def get_distance_to_lead(self) -> float:
        """Get distance to vehicle directly ahead. Returns inf if none."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        
        vehicles = self.world.get_actors().filter("vehicle.*")
        
        min_dist = float('inf')
        best_vehicle = None
        
        for v in vehicles:
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
        """Get absolute lane deviation (lateral distance from lane center)."""
        map_obj = self.world.get_map()
        ego_loc = self.get_ego_location()
        
        try:
            waypoint = map_obj.get_waypoint(ego_loc, project_to_road=True)
            lane_center = waypoint.transform.location
            rel_vec = ego_loc - lane_center
            
            right_vec = waypoint.transform.get_right_vector()
            lateral_dist = abs(rel_vec.x * right_vec.x + rel_vec.y * right_vec.y)
            
            return lateral_dist
        except:
            return 0.0
    
    def is_in_intersection(self) -> bool:
        """Check if ego is in an intersection."""
        map_obj = self.world.get_map()
        ego_loc = self.get_ego_location()
        
        try:
            waypoint = map_obj.get_waypoint(ego_loc, project_to_road=True)
            return waypoint.is_intersection
        except:
            return False
    
    def get_lane_marking_type(self) -> str:
        """Get lane marking type: 'continuous', 'dashed', or 'unknown'."""
        map_obj = self.world.get_map()
        ego_loc = self.get_ego_location()
        
        try:
            waypoint = map_obj.get_waypoint(ego_loc, project_to_road=True)
            
            if waypoint.right_lane_marking.type == carla.LaneMarkingType.Solid:
                return 'continuous'
            elif waypoint.right_lane_marking.type == carla.LaneMarkingType.Dashed:
                return 'dashed'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def get_indicator_state(self) -> Optional[str]:
        """Get turn indicator state: 'left', 'right', 'both', or None."""
        lights = self.ego_vehicle.get_light_state()
        
        if lights & carla.VehicleLightState.LeftBlinker:
            return 'left'
        elif lights & carla.VehicleLightState.RightBlinker:
            return 'right'
        elif lights & carla.VehicleLightState.All:
            return 'both'
        else:
            return None
    
    def get_steering_direction(self) -> str:
        """Get steering direction: 'left', 'right', or 'straight'."""
        control = self.ego_vehicle.get_control()
        steer = control.steer
        
        if steer < -0.1:
            return 'left'
        elif steer > 0.1:
            return 'right'
        else:
            return 'straight'
    
    def has_right_of_way(self) -> bool:
        """Check if ego has right of way (simplified placeholder)."""
        return True
    
    def is_vehicle_on_right(self, narrow: bool = False) -> bool:
        """Check if vehicle on right side. narrow=True for close detection."""
        ego_tf = self.ego_vehicle.get_transform()
        ego_loc = ego_tf.location
        ego_fwd = ego_tf.get_forward_vector()
        right_vec = ego_tf.get_right_vector()
        
        fwd_range = 15.0 if narrow else 30.0
        right_range = 1.5 if narrow else 3.0
        
        vehicles = self.world.get_actors().filter("vehicle.*")
        
        for v in vehicles:
            if v.id == self.ego_vehicle.id:
                continue
            
            v_loc = v.get_transform().location
            rel_vec = v_loc - ego_loc
            
            fwd_dist = rel_vec.x * ego_fwd.x + rel_vec.y * ego_fwd.y
            if 0 < fwd_dist < fwd_range:
                right_dist = rel_vec.x * right_vec.x + rel_vec.y * right_vec.y
                if 0 < right_dist < right_range:
                    return True
        
        return False
    
    # Static parameters
    
    def get_static_param(self, param_name: str, default: float = 0.0) -> float:
        """Get a static parameter."""
        return self.static_params.get(param_name, default)
    
    def set_static_param(self, param_name: str, value: float) -> None:
        """Set a static parameter."""
        self.static_params[param_name] = value
    
    # Scene data computation
    
    def compute_scene_data(self) -> Dict[str, Any]:
        """Compute all dynamic variables for guard evaluation."""
        return {
            # STOP rule
            'distance_to_sign': self.get_distance_to_sign(),
            'ego_speed': self.get_ego_speed(),
            
            # SAFE_DISTANCE rule
            'distance_to_lead': self.get_distance_to_lead(),
            'threshold_safe': self.get_static_param('threshold_safe'),
            'threshold_min': self.get_static_param('threshold_min'),
            
            # RIGHT_OF_WAY rule
            'ego_location': self.get_ego_location(),
            'in_intersection': self.is_in_intersection(),
            'precedence': self.has_right_of_way(),
            'broad_right_occupied': self.is_vehicle_on_right(narrow=False),
            'narrow_right_occupied': self.is_vehicle_on_right(narrow=True),
            
            # LANE_KEEPING rule
            'abs_lane_deviation': self.get_abs_lane_deviation(),
            'warning_threshold': self.get_static_param('warning_threshold'),
            'violation_threshold': self.get_static_param('violation_threshold'),
            'line_continuous': self.get_lane_marking_type() == 'continuous',
            'line_dashed': self.get_lane_marking_type() == 'dashed',
            'indicator': self.get_indicator_state(),
            'direction': self.get_steering_direction(),
        }
    
    def __repr__(self) -> str:
        return (f"VariableBinder(ego_id={self.ego_vehicle.id}, "
                f"params={self.static_params})")