import carla
import pygame
import numpy as np
import weakref
import threading


WIDTH  = 800
HEIGHT = 600


class RCADisplay:
    """
    Handles pygame window output (camera RGB) and input (keyboard + joystick).
    Designed to work with CARLA in RenderOffScreen mode.

    Usage:
        display = RCADisplay(world, ego_vehicle)
        display.start()
        # inside loop:
        display.tick()          # renders frame, returns False if quit
        control = display.get_control()
        reverse = display.reverse
        # on exit:
        display.destroy()
    """

    def __init__(self, world: carla.World, ego_vehicle: carla.Actor,
                 width: int = WIDTH, height: int = HEIGHT):
        self.world       = world
        self.ego_vehicle = ego_vehicle
        self.width       = width
        self.height      = height

        self._surface      = None
        self._surface_lock = threading.Lock()
        self._camera       = None

        self.control        = carla.VehicleControl()
        self.reverse        = False
        self.current_lights = int(carla.VehicleLightState.NONE)
        self.running        = True

        self._throttle_step = 0.03
        self._steer_step    = 0.04
        self._brake_step    = 0.1

        self._screen   = None
        self._joystick = None

    # ------------------------------------------------------------------

    def start(self):
        """Initialize pygame, spawn camera, begin listening."""
        pygame.init()
        pygame.joystick.init()

        self._screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("RCA  |  WASD/wheel · R=reverse · Q=quit")

        # Joystick (optional)
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

        # Spawn rear RGB camera attached to ego
        bp = self.world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(self.width))
        bp.set_attribute("image_size_y", str(self.height))
        bp.set_attribute("fov", "90")
        bp.set_attribute("sensor_tick", "0.05")

        # Third-person rear position
        cam_transform = carla.Transform(
            carla.Location(x=-5.5, z=2.5),
            carla.Rotation(pitch=-10)
        )
        self._camera = self.world.spawn_actor(bp, cam_transform, attach_to=self.ego_vehicle)

        weak_self = weakref.ref(self)
        self._camera.listen(lambda img: RCADisplay._on_image(weak_self, img))

    # ------------------------------------------------------------------

    @staticmethod
    def _on_image(weak_self, image):
        """Camera callback — converts CARLA image to pygame surface."""
        self = weak_self()
        if not self:
            return
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        with self._surface_lock:
            self._surface = surface

    # ------------------------------------------------------------------

    def tick(self) -> bool:
        """
        Process events, update display.
        Returns False when the user quits, True otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                elif event.key == pygame.K_r:
                    self.reverse = not self.reverse
            elif event.type == pygame.JOYBUTTONDOWN:
                self._handle_joystick_button(event.button)

        if not self.running:
            return False

        self._update_control()
        self._render()
        return True

    # ------------------------------------------------------------------

    def _handle_joystick_button(self, button: int):
        if button == 0:     # A -> toggle reverse
            self.reverse = not self.reverse
            if self.reverse:
                self.current_lights |= int(carla.VehicleLightState.Reverse)
            else:
                self.current_lights &= ~int(carla.VehicleLightState.Reverse)
            self.ego_vehicle.set_light_state(carla.VehicleLightState(self.current_lights))
        elif button == 1:   # B -> hazard
            self.current_lights ^= int(carla.VehicleLightState.LeftBlinker)
            self.current_lights ^= int(carla.VehicleLightState.RightBlinker)
            self.ego_vehicle.set_light_state(carla.VehicleLightState(self.current_lights))
        elif button == 4:   # paddle sx -> left blinker indicator
            self.current_lights ^= int(carla.VehicleLightState.LeftBlinker)
            self.ego_vehicle.set_light_state(carla.VehicleLightState(self.current_lights))
        elif button == 5:   # paddle dx -> right blinker indicator
            self.current_lights ^= int(carla.VehicleLightState.RightBlinker)
            self.ego_vehicle.set_light_state(carla.VehicleLightState(self.current_lights))

    # ------------------------------------------------------------------

    def _update_control(self):
        def clamp(v, lo, hi):
            return max(lo, min(hi, v))

        if self._joystick:
            steer_raw = self._joystick.get_axis(0)
            if abs(steer_raw) > 0.05:
                self.control.steer = steer_raw
            else:
                self.control.steer -= self.control.steer * 0.1

            throttle_joy = (self._joystick.get_axis(1) + 1.0) / 2.0
            brake_joy    = (self._joystick.get_axis(2) + 1.0) / 2.0

            if throttle_joy > 0.05:
                self.control.throttle = throttle_joy
                self.control.brake    = 0.0
            elif brake_joy > 0.05:
                self.control.brake    = brake_joy
                self.control.throttle = 0.0
            else:
                self.control.throttle = 0.0
                self.control.brake    = 0.0
        else:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                self.control.throttle = clamp(self.control.throttle + self._throttle_step, 0.0, 1.0)
                self.control.brake    = 0.0
            elif keys[pygame.K_s]:
                self.control.brake    = clamp(self.control.brake + self._brake_step, 0.0, 1.0)
                self.control.throttle = 0.0
            else:
                self.control.throttle = 0.0
                self.control.brake    = 0.0

            if keys[pygame.K_a]:
                self.control.steer = clamp(self.control.steer - self._steer_step, -1.0, 1.0)
            elif keys[pygame.K_d]:
                self.control.steer = clamp(self.control.steer + self._steer_step, -1.0, 1.0)
            else:
                self.control.steer -= self.control.steer * 0.1

        self.control.reverse = self.reverse

    # ------------------------------------------------------------------

    def _render(self):
        with self._surface_lock:
            surface = self._surface
        if surface is not None:
            self._screen.blit(surface, (0, 0))
        else:
            self._screen.fill((0, 0, 0))
        pygame.display.flip()

    # ------------------------------------------------------------------

    def get_control(self) -> carla.VehicleControl:
        return self.control

    def destroy(self):
        if self._camera is not None:
            self._camera.stop()
            self._camera.destroy()
            self._camera = None
        pygame.quit()
