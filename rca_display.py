import os
import carla
import pygame
import numpy as np
import weakref
import threading

# Allow input detection in background/notebook environments
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

WIDTH = 800
HEIGHT = 600

class RCADisplay:
    def __init__(self, world, ego_vehicle, width=WIDTH, height=HEIGHT):
        self.world = world
        self.ego_vehicle = ego_vehicle
        self.width = width
        self.height = height

        self._surface = None
        self._surface_lock = threading.Lock()
        self._camera = None

        self.control = carla.VehicleControl()
        self.reverse = False
        self.running = True

        self._screen = None
        self._joystick = None

    def start(self):
        pygame.init()
        pygame.joystick.init()
        self._screen = pygame.display.set_mode((self.width, self.height))
        
        # Force event polling to initialize XInput device
        pygame.event.pump()
        if pygame.joystick.get_count() > 0:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

        bp = self.world.get_blueprint_library().find("sensor.camera.rgb")
        bp.set_attribute("image_size_x", str(self.width))
        bp.set_attribute("image_size_y", str(self.height))
        bp.set_attribute("fov", "90")

        cam_transform = carla.Transform(carla.Location(x=-5.5, z=2.5), carla.Rotation(pitch=-10))
        self._camera = self.world.spawn_actor(bp, cam_transform, attach_to=self.ego_vehicle)
        
        weak_self = weakref.ref(self)
        self._camera.listen(lambda img: RCADisplay._on_image(weak_self, img))

    @staticmethod
    def _on_image(weak_self, image):
        self = weak_self()
        if not self: return
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3][:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        with self._surface_lock:
            self._surface = surface

    def tick(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reverse = not self.reverse

        if not self.running:
            return False

        self._update_control()
        self._render()
        return True

    def _update_control(self):
        if self._joystick:
            steer = self._joystick.get_axis(0)
            # Normalize triggers: -1.0 (released) to 1.0 (fully pressed) -> 0.0 to 1.0
            throttle = (self._joystick.get_axis(1) + 1.0) / 2.0
            brake = (self._joystick.get_axis(2) + 1.0) / 2.0

            self.control.steer = steer**3 if abs(steer) > 0.05 else 0.0
            self.control.throttle = throttle if throttle > 0.05 else 0.0
            self.control.brake = brake if brake > 0.05 else 0.0
        else:
            keys = pygame.key.get_pressed()
            self.control.throttle = 1.0 if keys[pygame.K_w] else 0.0
            self.control.steer = -0.5 if keys[pygame.K_a] else (0.5 if keys[pygame.K_d] else 0.0)
            self.control.brake = 1.0 if keys[pygame.K_s] else 0.0

        self.control.reverse = self.reverse
        # self.ego_vehicle.apply_control(self.control)

    def get_control(self):
        return self.control
    
    def _render(self):
        with self._surface_lock:
            if self._surface:
                self._screen.blit(self._surface, (0, 0))
        pygame.display.flip()

    def destroy(self):
        if self._camera:
            self._camera.destroy()
        pygame.quit()