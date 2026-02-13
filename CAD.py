import pygame
import math
from line import Line

# ==========================================
# 1. The Snapping Logic (Pure Math)
# ==========================================
class SnapEngine:
    def __init__(self, pixel_radius=10):
        self.radius = pixel_radius
        self.sq_radius = pixel_radius ** 2

    def get_snapped_pos(self, current_pos, lines, anchor_pos=None):
        """
        Calculates the best snap position.
        1. Checks for Vertex Snaps (endpoints of existing lines).
        2. If no vertex snap and anchor_pos exists, checks Axis Snaps (H/V).
        """
        x, y = current_pos
        
        # --- Priority 1: Vertex Snapping (Snap to existing points) ---
        for line in lines:
            # Check both start (a) and end (b) of every line
            for pt in [line.a, line.b]:
                # Assuming pt is (x, y) or has .x .y
                px, py = pt if isinstance(pt, tuple) else (pt.x, pt.y)
                
                dist_sq = (x - px)**2 + (y - py)**2
                if dist_sq <= self.sq_radius:
                    return (px, py) # Return immediately on first snap

        # --- Priority 2: Axis Snapping (Horizontal/Vertical) ---
        # Only happens if we have a starting point (anchor_pos)
        if anchor_pos:
            ax, ay = anchor_pos
            
            # Snap Y (Horizontal line)
            if abs(y - ay) < self.radius:
                y = ay
            # Snap X (Vertical line)
            if abs(x - ax) < self.radius:
                x = ax

        return (x, y)

# ==========================================
# 2. The Editor State (Logic & storage)
# ==========================================
class Editor:
    def __init__(self):
        self.lines = []
        self.snap_engine = SnapEngine(pixel_radius=10)
        
        # State
        self.is_drawing = False
        self.start_pos = None  # The point where we clicked first
        self.current_mouse_pos = (0, 0)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.current_mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._cancel_or_undo()

    def _handle_click(self, raw_mouse_pos):
        # 1. Calculate where the click actually lands (considering snaps)
        snapped_pos = self.snap_engine.get_snapped_pos(
            raw_mouse_pos, 
            self.lines, 
            self.start_pos
        )

        if not self.is_drawing:
            # Start new line
            self.start_pos = snapped_pos
            self.is_drawing = True
        else:
            # Finish line
            new_line = Line(self.start_pos, snapped_pos)
            self.lines.append(new_line)
            
            # Chain drawing: End of this line is start of next
            self.start_pos = snapped_pos 

    def _cancel_or_undo(self):
        if self.is_drawing:
            self.is_drawing = False
            self.start_pos = None
        elif self.lines:
            self.lines.pop()

    def draw(self, screen):
        # Draw all committed lines
        for line in self.lines:
            line.draw(screen)

        # Draw preview line
        if self.is_drawing and self.start_pos:
            # We calculate the snap AGAIN here for visual feedback
            # This ensures the preview looks exactly like the result will look
            target_pos = self.snap_engine.get_snapped_pos(
                self.current_mouse_pos, 
                self.lines, 
                self.start_pos
            )
            
            # Draw a faint preview line
            pygame.draw.line(screen, (150, 150, 150), self.start_pos, target_pos, 1)
            
            # Optional: Draw a circle showing where it's snapping
            pygame.draw.circle(screen, (0, 255, 0), target_pos, 3, 1)


# ==========================================
# 3. Main Setup & Loop
# ==========================================
pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Refactored Snapping")
clock = pygame.time.Clock()

editor = Editor() # Instantiate our logic handler

running = True
dt = 1 / 60 
accumulator = 0.0

while running:
    # --- Time ---
    frame_time = clock.tick(60) / 1000.0
    accumulator += frame_time

    # --- Input ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            # Delegate specific events to the editor
            editor.handle_event(event)

    # --- Fixed Update (if you had physics, it would go here) ---
    while accumulator >= dt:
        accumulator -= dt

    # --- Render ---
    screen.fill("black")
    editor.draw(screen)
    pygame.display.flip()

pygame.quit()