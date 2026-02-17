import pygame
import math
from line import Line
from snapengine import SnapEngine
from pygame_widgets.button import Button
import pygame_widgets
from camera import Camera


class Editor:
    def __init__(self,screen):
        self.lines = []
        self.snap_engine = SnapEngine(pixel_radius=10)
        
        # State
        self.is_drawing = False
        self.start_pos = None  # The point where we clicked first
        self.current_mouse_pos = (0, 0)
        self.screen = screen
        self.finished = False
        
        self.setup_ui()
        
    def setup_ui(self):
        
        self.finish_button = Button(
            self.screen,
            50, 50,
            150, 50,
            text='Finish',
            onClick=self.finish
        )
        
    # Update signature to accept camera
    def handle_event(self, event, camera):
        if event.type == pygame.MOUSEMOTION:
            self.current_mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos, camera) 

        # --- NEW: Escape Key Logic ---
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._handle_escape()

    def _handle_escape(self):
        if self.is_drawing:
            # 1. If mid-drawing, just stop drawing and "throw away" the start point
            self.is_drawing = False
            self.start_pos = None
            print("Drawing canceled.")
        elif self.lines:
            # 2. If not drawing, remove the last line (Undo)
            removed_line = self.lines.pop()
            print("Last line removed.")

    # Update click logic to convert FIRST
    def _handle_click(self, screen_mouse_pos, camera):
        # 1. Convert Screen (Pixels) -> World (Meters)
        # You need to implement screen_to_world in your Camera class!
        world_mouse_pos = camera.screen_to_world(screen_mouse_pos)

        # 2. Snap Logic now happens in World Space (consistent with your Lines)
        snapped_pos = self.snap_engine.get_snapped_pos(
            world_mouse_pos, 
            self.lines, 
            camera.scale,
            self.start_pos
        )

        if not self.is_drawing:
            self.start_pos = snapped_pos
            self.is_drawing = True
        else:
            new_line = Line(self.start_pos, snapped_pos)
            self.lines.append(new_line)
            self.start_pos = snapped_pos

    def _cancel_or_undo(self):
        if self.is_drawing:
            self.is_drawing = False
            self.start_pos = None
        elif self.lines:
            self.lines.pop()
            
    def update_buttons(self,events):
        pygame_widgets.update(events)

    def draw(self, screen, camera):
        # Draw all committed lines (Safe: Line.draw uses camera)
        for line in self.lines:
            line.draw(screen, camera)

        # Draw preview line
        if self.is_drawing and self.start_pos:
            # 1. Get current mouse in World Space
            world_mouse = camera.screen_to_world(self.current_mouse_pos)

            # 2. Calculate Snap in World Space
            target_world_pos = self.snap_engine.get_snapped_pos(
                world_mouse, 
                self.lines, 
                camera.scale,
                self.start_pos
            )
            
            # 3. Convert BOTH points back to Screen Space for drawing
            # self.start_pos is already World Space (from _handle_click)
            p1_screen = camera.to_screen(self.start_pos)
            p2_screen = camera.to_screen(target_world_pos)
            
            # 4. Draw using Screen Coordinates
            pygame.draw.line(screen, (150, 150, 150), p1_screen, p2_screen, 1)
            pygame.draw.circle(screen, (0, 255, 0), p2_screen, 3, 1)
            
    def finish(self):
        self.finished = True
        pass