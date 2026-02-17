import pygame
import math
from line import Line
from editor import Editor
from snapengine import SnapEngine
from pygame_widgets.button import Button
import pygame_widgets
from mesher import Mesher
from quad import Quad
from camera import Camera


pygame.init()
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Refactored Snapping")
clock = pygame.time.Clock()


editor = Editor(screen) # Instantiate our logic handler

current_state = "EDITOR"
mesher = None


running = True
dt = 1 / 60 
accumulator = 0.0

camera = Camera()

# Main loop
while running:
    # --- Time ---
    frame_time = clock.tick(60) / 1000.0
    accumulator += frame_time

    # --- Input ---
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEWHEEL:
            camera.handle_zoom(pygame.mouse.get_pos(), event.y)
            
        if current_state == "EDITOR":
            editor.handle_event(event,camera)
            editor.update_buttons(events)

            if editor.finished:
                lines = editor.lines
                mesher = Mesher(screen, lines)
                mesher.mesh()
                current_state = "MESHER"


    # --- Fixed Update 
    while accumulator >= dt:
        accumulator -= dt

    # --- Render ---

    screen.fill("black")
    if current_state == "EDITOR":
        editor.draw(screen,camera)
        editor.update_buttons(events)
    elif current_state == "MESHER":
        mesher.draw(screen,camera)
    pygame.display.flip()

pygame.quit()