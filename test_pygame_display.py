import pygame
import sys
import threading
from datetime import datetime
from typing import List, Tuple
from view.hud_drawer import HudDrawer, Notification
from models.state import StateType

WIDTH = 800
HEIGHT = 600
FPS = 30


class MockPygameDisplay:
    """Mock di PygameDisplay per testare HudDrawer senza CARLA."""
    
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width = width
        self.height = height
        self._screen = None
        self.running = True
        self.clock = None
        self.pressed_keys = []
    
    def start(self):
        """Inizializza pygame."""
        pygame.init()
        self._screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("HudDrawer Test (Press 'W' for WARNING, 'V' for VIOLATION)")
        self.clock = pygame.time.Clock()
    
    def tick(self):
        """Gestisce gli eventi e ritorna True se il programma deve continuare."""
        self.pressed_keys = []
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    self.running = False
                else:
                    # Traccia i tasti premuti
                    self.pressed_keys.append(event.key)
        
        # Riempie lo schermo con colore grigio
        self._screen.fill((40, 40, 40))
        self.clock.tick(FPS)
        
        return self.running
    
    def destroy(self):
        """Pulisce pygame."""
        pygame.quit()


def main():
    """Main function per testare HudDrawer senza connessione a CARLA."""
    
    # Crea il mock display
    display = MockPygameDisplay(WIDTH, HEIGHT)
    display.start()
    
    # Crea l'HUD drawer
    hud = HudDrawer(display)
    
    try:
        while display.tick():
            # Controlla i tasti premuti per generare notifiche
            if pygame.K_w in display.pressed_keys:
                notif = Notification(
                    "Lane Keeping",
                    StateType.WARNING,
                    duration=3.0
                )
                hud.notify(notif)
            
            if pygame.K_v in display.pressed_keys:
                notif = Notification(
                    "Lane Keeping",
                    StateType.VIOLATION,
                    duration=3.0
                )
                hud.notify(notif)
            
            # Disegna le notifiche
            hud._draw_notifications()
            pygame.display.flip()
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        display.destroy()


if __name__ == "__main__":
    main()
