import os
import carla
import pygame
import numpy as np
import weakref
import threading

# Allow input detection in background/notebook environments
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

# Default window size (freely resizable at runtime)
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600

# Internal camera render resolution (fixed — independent from window size)
RENDER_WIDTH = 800
RENDER_HEIGHT = 600


class PygameDisplay:
    def __init__(
        self,
        world,
        ego_vehicle,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        render_width: int = RENDER_WIDTH,
        render_height: int = RENDER_HEIGHT,
    ):
        """
        Handles rendering the camera feed and processing user input for controlling the vehicle.

        Parameters
        -------
        world: carla.World
            The Carla world instance.
        ego_vehicle: carla.Vehicle
            The ego vehicle to control.
        width: int
            Initial window width in pixels (resizable at runtime).
        height: int
            Initial window height in pixels (resizable at runtime).
        render_width: int
            Camera sensor resolution width (fixed after start).
        render_height: int
            Camera sensor resolution height (fixed after start).
        """
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.width = width
        self.height = height
        self._render_width = render_width
        self._render_height = render_height

        self._surface = None
        self._surface_lock = threading.Lock()
        self._camera = None
        self._camera_views = [
            carla.Transform(carla.Location(x=-5.5, z=2.5),
                            carla.Rotation(pitch=-10)),
            carla.Transform(carla.Location(x=-1.8, z=5),
                            carla.Rotation(pitch=-30)),
        ]
        self._camera_view_idx = 0

        self._control = carla.VehicleControl()
        self.reverse = False
        self.running = True

        self._screen = None
        self._joystick = None
        self.current_lights = 0
        self.hud_drawer = None

    @property
    def control(self):
        return self._control

    def start(self):
        pygame.init()
        pygame.joystick.init()
        self._screen = pygame.display.set_mode(
            (self.width, self.height), pygame.RESIZABLE)

        pygame.event.pump()
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

        bp = self.world.get_blueprint_library().find("sensor.camera.rgb")

        bp.set_attribute("image_size_x", str(self._render_width))
        bp.set_attribute("image_size_y", str(self._render_height))
        bp.set_attribute("fov", "90")

        cam_transform = self._camera_views[self._camera_view_idx]
        self._camera = self.world.spawn_actor(
            bp, cam_transform, attach_to=self.ego_vehicle)

        weak_self = weakref.ref(self)
        self._camera.listen(
            lambda img: PygameDisplay._on_image(weak_self, img))

    @staticmethod
    def _on_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3][:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        with self._surface_lock:
            self._surface = surface

    def _handle_reverse(self):
        '''Toggle reverse gear and update light state accordingly.'''
        self.reverse = not self.reverse
        if self.reverse:
            self.current_lights |= int(carla.VehicleLightState.Reverse)
        else:
            self.current_lights &= ~int(carla.VehicleLightState.Reverse)
        self.ego_vehicle.set_light_state(
            carla.VehicleLightState(self.current_lights))

    def _toggle_camera_view(self):
        """Switch between top and low camera viewpoints."""
        if not self._camera:
            return
        self._camera_view_idx = (
            self._camera_view_idx + 1) % len(self._camera_views)
        self._camera.set_transform(self._camera_views[self._camera_view_idx])

    def tick(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.size
                self._screen = pygame.display.set_mode(
                    (self.width, self.height), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self._handle_reverse()
                elif event.key == pygame.K_c:
                    self._toggle_camera_view()
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                elif event.key == pygame.K_LEFT and not self._joystick:
                    self._toggle_blinker(left=True)
                elif event.key == pygame.K_RIGHT and not self._joystick:
                    self._toggle_blinker(left=False)
            elif event.type == pygame.JOYBUTTONDOWN and self._joystick:
                self._handle_joystick_button(event.button)

        if not self.running:
            return False

        self._update_control()
        self._render()
        return True

    def _update_control(self):
        if self._joystick:
            steer = self._joystick.get_axis(0)

            throttle = (self._joystick.get_axis(1) + 1.0) / 2.0
            brake = (self._joystick.get_axis(2) + 1.0) / 2.0

            self._control.steer = steer**3 if abs(steer) > 0.05 else 0.0
            self._control.throttle = throttle if throttle > 0.05 else 0.0
            self._control.brake = brake if brake > 0.05 else 0.0
        else:
            keys = pygame.key.get_pressed()
            self._control.throttle = 1.0 if keys[pygame.K_w] else 0.0
            self._control.steer = - \
                0.5 if keys[pygame.K_a] else (0.5 if keys[pygame.K_d] else 0.0)
            self._control.brake = 1.0 if keys[pygame.K_s] else 0.0

        self._control.reverse = self.reverse

    def _toggle_blinker(self, left: bool):
        """Toggle left or right blinker, turning off the opposite one if active."""
        if left:
            own_flag = int(carla.VehicleLightState.LeftBlinker)
            other_flag = int(carla.VehicleLightState.RightBlinker)
        else:
            own_flag = int(carla.VehicleLightState.RightBlinker)
            other_flag = int(carla.VehicleLightState.LeftBlinker)

        if self.current_lights & own_flag:
            self.current_lights &= ~own_flag
        else:
            self.current_lights &= ~other_flag
            self.current_lights |= own_flag

        self.ego_vehicle.set_light_state(
            carla.VehicleLightState(self.current_lights))

    def _handle_joystick_button(self, button: int):
        """Handle joystick button presses for light control."""
        if button == 0:     # A → toggle reverse
            self._handle_reverse()
        elif button == 1:   # B → hazard (both blinkers)
            self.current_lights ^= int(carla.VehicleLightState.LeftBlinker)
            self.current_lights ^= int(carla.VehicleLightState.RightBlinker)
            self.ego_vehicle.set_light_state(
                carla.VehicleLightState(self.current_lights))
        elif button == 3:   # Y → toggle camera view
            self._toggle_camera_view()
        elif button == 4:   # paddle sx → left blinker
            self._toggle_blinker(left=True)
        elif button == 5:   # paddle dx → right blinker
            self._toggle_blinker(left=False)

    def _render(self):
        self._screen.fill((0, 0, 0))

        with self._surface_lock:
            if self._surface:
                src_w, src_h = self._surface.get_size()

                scale = min(self.width / src_w, self.height / src_h)
                dst_w = int(src_w * scale)
                dst_h = int(src_h * scale)
                offset_x = (self.width - dst_w) // 2
                offset_y = (self.height - dst_h) // 2
                scaled_surface = pygame.transform.scale(
                    self._surface, (dst_w, dst_h))
                self._screen.blit(scaled_surface, (offset_x, offset_y))

        if self.hud_drawer:
            self.hud_drawer._draw_notifications()

        pygame.display.flip()

    def destroy(self):
        if self._camera:
            self._camera.destroy()
        pygame.quit()
