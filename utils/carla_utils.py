import carla
import numpy as np
import random
import time
import random
import json


def world_connect(name="localhost", port=2000, timeout=20.0, map_name=None):
    """Connect to the CARLA world and return the world, spectator, and client objects."""
    client = carla.Client(name, port)
    client.set_timeout(timeout)

    if map_name:
        print(f"Loading of {map_name} in progress...")
        world = client.load_world(map_name)
        print("Map loaded successfully!")
    else:
        world = client.get_world()

    spectator = world.get_spectator()
    return world, spectator, client


def move_spectator_to(transform, spectator, distance=7.0, z=3.0, pitch=-15.0):
    """Move the spectator to a position behind and above the given transform."""
    back = transform.location - transform.get_forward_vector() * distance
    loc = carla.Location(back.x, back.y, back.z + z)
    rot = carla.Rotation(pitch=pitch, yaw=transform.rotation.yaw, roll=0.0)
    spectator.set_transform(carla.Transform(loc, rot))


def spawn_vehicle(world, spawn_index=0, vehicle_filter="vehicle.tesla.model3", autopilot=False):
    """Spawn a vehicle at a random spawn point."""
    points = world.get_map().get_spawn_points()
    if not points:
        raise RuntimeError("No spawn points found")
    bps = world.get_blueprint_library().filter(vehicle_filter)
    if not bps:
        bps = world.get_blueprint_library().filter("vehicle.*")
    for k in range(len(points)):
        actor = world.try_spawn_actor(random.choice(
            bps), points[(spawn_index + k) % len(points)])
        if actor is not None:
            actor.set_autopilot(autopilot)
            return actor
    raise RuntimeError("Could not spawn vehicle")


def spawn_vehicle_ahead(world, ref_vehicle, distances=(20.0, 28.0, 36.0), same_lane_first=True, retries=6):
    ego_tf = ref_vehicle.get_transform()
    ego_loc = ego_tf.location
    fwd = ego_tf.get_forward_vector()
    right = ego_tf.get_right_vector()

    bps = world.get_blueprint_library().filter("vehicle.*")
    if not bps:
        raise RuntimeError("No vehicle blueprints found")

    # Phase 1: try exact transforms straight ahead of ego so the target is visually in front.
    direct = sorted(set(float(d) for d in distances))
    direct += [d + 4.0 for d in direct]
    for d in direct:
        loc = ego_loc + fwd * d + right * 0.0
        loc.z += 0.30
        tf = carla.Transform(loc, ego_tf.rotation)
        actor = world.try_spawn_actor(random.choice(bps), tf)
        if actor is not None:
            actor.set_autopilot(False)
            return actor

    # Phase 2: fallback to road waypoints in front.
    road_map = world.get_map()
    ego_wp = road_map.get_waypoint(
        ego_loc, project_to_road=True, lane_type=carla.LaneType.Driving)

    wp_candidates = []
    d_pool = sorted(set(float(d) for d in distances) |
                    set(float(d) + 8.0 for d in distances))
    for d in d_pool:
        try:
            cands = ego_wp.next(float(d))
        except RuntimeError:
            cands = []
        if same_lane_first:
            cands = sorted(
                cands,
                key=lambda w: (
                    w.road_id != ego_wp.road_id,
                    w.lane_id != ego_wp.lane_id,
                    abs(w.lane_id - ego_wp.lane_id),
                ),
            )
        wp_candidates.extend(cands)

    for _ in range(max(1, int(retries))):
        for wp in wp_candidates:
            actor = world.try_spawn_actor(random.choice(bps), wp.transform)
            if actor is not None:
                actor.set_autopilot(False)
                return actor
        world.tick()
        time.sleep(0.02)

    # Phase 3: fallback to an already existing vehicle in front.
    best = None
    best_d = float("inf")
    for a in world.get_actors().filter("vehicle.*"):
        if a.id == ref_vehicle.id:
            continue
        loc = a.get_transform().location
        rel = loc - ego_loc
        d_fwd = rel.x * fwd.x + rel.y * fwd.y
        d_lat = abs(rel.x * (-fwd.y) + rel.y * fwd.x)
        if d_fwd > 6.0 and d_lat < 4.0 and d_fwd < best_d:
            best = a
            best_d = d_fwd

    if best is not None:
        try:
            best.set_autopilot(False)
        except RuntimeError:
            pass
        return best

    raise RuntimeError("Could not spawn or find a target vehicle ahead")


def spawn_camera(world, attach_to, transform, width=640, height=360, fov=95, tick=0.05):
    """Spawn a camera sensor attached to the given actor."""
    bp = world.get_blueprint_library().find("sensor.camera.rgb")
    bp.set_attribute("image_size_x", str(width))
    bp.set_attribute("image_size_y", str(height))
    bp.set_attribute("fov", str(fov))
    bp.set_attribute("sensor_tick", str(tick))
    return world.spawn_actor(bp, transform, attach_to=attach_to)


def spawn_lidar(world, attach_to, transform, channels=32, points_per_second=56000, rotation_frequency=20, range_m=35):
    """Spawn a LiDAR sensor attached to the given actor."""
    bp = world.get_blueprint_library().find("sensor.lidar.ray_cast")
    bp.set_attribute("channels", str(channels))
    bp.set_attribute("points_per_second", str(points_per_second))
    bp.set_attribute("rotation_frequency", str(rotation_frequency))
    bp.set_attribute("range", str(range_m))
    return world.spawn_actor(bp, transform, attach_to=attach_to)


def image_to_bgr(image):
    """Convert a CARLA image to a NumPy array in BGR format."""
    arr = np.frombuffer(image.raw_data, dtype=np.uint8)
    arr = np.reshape(arr, (image.height, image.width, 4))
    return arr[:, :, :3].copy()


def lidar_to_numpy(measurement):
    """Convert a CARLA LiDAR measurement to a NumPy array of shape (N, 4)."""
    pts = np.frombuffer(measurement.raw_data, dtype=np.float32)
    return np.reshape(pts, (-1, 4))


def safe_destroy(actors):
    """Safely destroy a list of CARLA actors, ignoring any that are already destroyed."""
    for a in actors:
        if a is not None:
            try:
                a.destroy()
            except RuntimeError:
                pass


def draw_on_screen(world, transform, content="O", color=carla.Color(0, 255, 0), life_time=20):
    world.debug.draw_string(transform.location, content,
                            color=color, life_time=life_time)


def spawn_random_vehicle_no_bike(world, spawn_index=0, autopilot=False):
    """Spawn a random vehicle excluding bicycles"""
    blueprint_library = world.get_blueprint_library()
    all_vehicles = blueprint_library.filter("vehicle.*")
    vehicles = [bp for bp in all_vehicles if "bicycle" not in bp.id]
    if not vehicles:
        vehicles = all_vehicles

    points = world.get_map().get_spawn_points()
    if not points:
        raise RuntimeError("No spawn points found")

    for k in range(len(points)):
        vehicle_bp = random.choice(vehicles)
        actor = world.try_spawn_actor(
            vehicle_bp, points[(spawn_index + k) % len(points)])
        if actor is not None:
            actor.set_autopilot(autopilot)
            return actor
    raise RuntimeError("Could not spawn vehicle")


def write_log(filename, frame_count, timestamp, control, scene_data, reverse):
    """Write frame data to JSON log file"""
    log_entry = {
        'frame': frame_count,
        'timestamp': timestamp,
        'reverse': reverse,
        'control': {
            'throttle': float(control.throttle),
            'brake': float(control.brake),
            'steer': float(control.steer)
        },
        'scene_data': {}
    }
    for key, value in scene_data.items():
        if hasattr(value, '__dict__'):
            log_entry['scene_data'][key] = str(value)
        elif isinstance(value, (int, float, str, bool, type(None))):
            log_entry['scene_data'][key] = value
        else:
            log_entry['scene_data'][key] = str(value)

    with open(filename, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')


def spawn_random_vehicle_no_bike_at(world, transform, vehicle_filter="vehicle.tesla.model3", autopilot=False):
    """Spawn a random non-bicycle vehicle at a fixed transform."""
    bps = world.get_blueprint_library().filter(vehicle_filter)
    all_vehicles = bps.filter("vehicle.*")
    vehicles = [bp for bp in all_vehicles if "bicycle" not in bp.id]
    if not vehicles:
        vehicles = all_vehicles

    actor = world.try_spawn_actor(random.choice(vehicles), transform)
    if actor is None:
        raise RuntimeError(
            "Could not spawn vehicle at the requested transform")

    actor.set_autopilot(autopilot)
    return actor
