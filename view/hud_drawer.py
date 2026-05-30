from datetime import datetime
import threading
from typing import List
import pygame

from models.state import StateType
from view.pygame_display import PygameDisplay


class Notification:
    def __init__(self, title: str, type: StateType, duration: float = 3.0):
        """
        Args:
            title: Title of the notification
            type: Type of the notification
            duration: Duration in seconds of the notification (default 3.0)
        """
        self.title = title
        self.type = type
        self.duration = duration
        self.creation_time = datetime.now()

    def is_expired(self) -> bool:
        """Checks if the notification has expired."""
        elapsed = (datetime.now() - self.creation_time).total_seconds()
        return elapsed > self.duration
    
    def get_visibility(self) -> float:
        """Returns visibility factor (0.0 to 1.0) based on elapsed time."""
        elapsed = (datetime.now() - self.creation_time).total_seconds()
        if elapsed > self.duration * 0.8:
            visibility = 1 - (elapsed - self.duration * 0.8) / (self.duration * 0.2)
        else:
            visibility = 1.0
        return max(0.0, min(1.0, visibility))
    

class HudDrawer:
    """Classe per disegnare l'HUD (Head-Up Display) con le notifiche di violazione."""
    
    def __init__(self, display: PygameDisplay):
        self.display = display
        self.notifications: List[Notification] = []
        
        self._lock = threading.Lock()
        
    def notify(self, notification: Notification):
        """Adds a new notification to be displayed."""
        with self._lock:
            self.notifications.append(notification)
            
    def _draw_notifications(self):
        """Draws the active violation notifications on the screen."""
        with self._lock:
            self.notifications = [n for n in self.notifications if not n.is_expired()]
            notifications = list(self.notifications)

        notifications.sort(key=lambda n: n.creation_time)
        
        notification_height = 95
        start_y = 100
        
        for i, notification in enumerate(notifications):
            y = start_y + i * (notification_height + 15)
            if y + notification_height > self.display.height - 80:
                break
            
            alpha = notification.get_visibility() * 255
            self._draw_notification_box(
                notification,
                y,
                alpha
            )
    
    def _draw_notification_box(self, notification: Notification, y: int, alpha: int):
        """Draws a single notification box"""

        BOX_W   = 430
        BOX_H   = 95
        RADIUS  = 16
        PAD_L   = 22         
        ICON_SZ = 36        
        TEXT_X  = PAD_L + ICON_SZ + 14
        TITLE_Y = 13
        SUB_Y   = 40
        TIME_Y  = 63

        x = self.display.width - BOX_W - 20
        is_violation = notification.type == StateType.VIOLATION
        accent = (220, 50, 50) if is_violation else (255, 175, 0)

        if not hasattr(self, '_notif_fonts'):
            self._notif_fonts = {
                'title': pygame.font.SysFont("arial", 20, bold=True),
                'sub':   pygame.font.SysFont("arial", 13),
                'time':  pygame.font.SysFont("arial", 13, bold=True),
                'icon':  pygame.font.SysFont("arial", 22, bold=True),
            }
        fnt = self._notif_fonts

        def _apply_alpha(surf: pygame.Surface, a: int) -> None:
            if a < 255:
                mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
                mask.fill((255, 255, 255, a))
                surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


        for dx, dy, pad, sh_a in [(3, 6, 8, 18), (2, 5, 5, 28), (1, 4, 3, 42)]:
            sw, sh = BOX_W + pad * 2, BOX_H + pad * 2
            shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, sh_a),
                            (0, 0, sw, sh), border_radius=RADIUS + pad // 2)
            _apply_alpha(shadow, alpha)
            self.display._screen.blit(shadow, (x - pad + dx, y - pad + dy))

        surf = pygame.Surface((BOX_W, BOX_H), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pygame.draw.rect(surf, (18, 18, 18, 255),
                        (0, 0, BOX_W, BOX_H), border_radius=RADIUS)


        icon_cx = PAD_L + ICON_SZ // 2
        icon_cy = BOX_H // 2 + 2 

        if is_violation:
            pygame.draw.circle(surf, (*accent, 255), (icon_cx, icon_cy), ICON_SZ // 2)
            excl = fnt['icon'].render("!", True, (255, 255, 255))
            surf.blit(excl, excl.get_rect(center=(icon_cx, icon_cy)))
        else:
            h = ICON_SZ // 2
            tri = [
                (icon_cx,      icon_cy - h + 1),   # apex
                (icon_cx - h,  icon_cy + h - 1),   # bottom-left
                (icon_cx + h,  icon_cy + h - 1),   # bottom-right
            ]
            pygame.draw.polygon(surf, (*accent, 255), tri)
            excl = fnt['icon'].render("!", True, (20, 14, 0))
            surf.blit(excl, excl.get_rect(center=(icon_cx, icon_cy + 3)))

        surf.blit(
            fnt['title'].render(notification.title, True, (255, 255, 255)),
            (TEXT_X, TITLE_Y)
        )

        subtitle ="Violation detected" if is_violation else "Warning"
        surf.blit(
            fnt['sub'].render(subtitle, True, (185, 185, 185)),
            (TEXT_X, SUB_Y)
        )

        ts = notification.creation_time.strftime("%I:%M %p")
        ts = ts[1:] if ts.startswith("0") else ts
        surf.blit(
            fnt['time'].render(ts, True, accent),
            (TEXT_X, TIME_Y)
        )

        _apply_alpha(surf, alpha)
        self.display._screen.blit(surf, (x, y))