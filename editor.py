import pygame
import math
from line import Line
from snapengine import SnapEngine
from pygame_widgets.button import Button
import pygame_widgets


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
            
    def update_buttons(self,events):
        pygame_widgets.update(events)

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
            
    def finish(self):
        self.finished = True
        pass