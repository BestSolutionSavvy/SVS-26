import pygame
from view.hud_drawer import HudDrawer, Notification
from models.state import StateType

WIDTH = 800
HEIGHT = 600
FPS = 30


class MockPygameDisplay:
    """A simple display wrapper for running the HUD demo."""

    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self._screen = None
        self.running = True
        self.clock = None
        self.pressed_keys = []

    def start(self):
        pygame.init()
        self._screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(
            "HudDrawer Demo (Press 'W' for WARNING, 'V' for VIOLATION)")
        self.clock = pygame.time.Clock()

    def tick(self):
        self.pressed_keys = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                else:
                    self.pressed_keys.append(event.key)
        self._screen.fill((40, 40, 40))
        self.clock.tick(FPS)
        return self.running

    def destroy(self):
        pygame.quit()


def hud_demo():
    display = MockPygameDisplay(WIDTH, HEIGHT)
    display.start()
    hud = HudDrawer(display)

    try:
        while display.tick():
            if pygame.K_w in display.pressed_keys:
                hud.notify(Notification("Lane Keeping",
                           StateType.WARNING, duration=3.0))
            if pygame.K_v in display.pressed_keys:
                hud.notify(Notification("Lane Keeping",
                           StateType.VIOLATION, duration=3.0))
            hud._draw_notifications()
            pygame.display.flip()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        display.destroy()


if __name__ == "__main__":
    hud_demo()
