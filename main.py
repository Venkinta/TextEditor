import pygame
import math
from line import Line
from editor import Editor
from snapengine import SnapEngine
from pygame_widgets.button import Button
import pygame_widgets
from mesher import Mesher
from solver import Solver
from quad import Quad
from camera import Camera
from physics_editor import PhysicsEditor
from OpenGL.GL import *
import imgui
from imgui.integrations.pygame import PygameRenderer

import cProfile
import pstats

def run_app():
    pygame.init()
    WIDTH, HEIGHT = 1280, 720
    # DOUBLEBUF is for smooth rendering, OPENGL initializes the 3D context
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.OPENGL)
    def init_gpu(width, height):
        # This tells OpenGL how to map its coordinates to your window pixels
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, height, 0, -1, 1) # (left, right, bottom, top, near, far)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glEnable(GL_BLEND) # For transparent UI
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Call it like this:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.OPENGL)
    init_gpu(WIDTH, HEIGHT)
    clock = pygame.time.Clock()
    imgui.create_context()
    renderer = PygameRenderer()

    imgui.get_io().display_size = (WIDTH, HEIGHT)


    editor = Editor(screen, renderer) # Instantiate our logic handler

    current_state = "EDITOR"
    mesher = None
    physicseditor = None


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
                # 1. Let ImGui process the click for the "Finish CAD" button
                renderer.process_event(event)
                
                # 2. Only draw/snap lines if we aren't clicking the UI
                if not imgui.get_io().want_capture_mouse:
                    editor.handle_event(event, camera)

                if editor.finished:
                    lines = editor.lines
                    physicseditor = PhysicsEditor(screen,lines,renderer)
                    current_state = "PHYSICS"

            if current_state == "PHYSICS":
                physicseditor.renderer.process_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button ==1:
                        
                        if not imgui.get_io().want_capture_mouse:
                            physicseditor.handle_selection(camera.screen_to_world(event.pos))


                if physicseditor.finished:
                    lines = physicseditor.lines
                    mesher = Mesher(screen, lines,physicseditor.n_layers,physicseditor.growth_factor,
                                    physicseditor.thickness,physicseditor.boundary_spacing,physicseditor.r,renderer)
                    mesher.mesh()
                    current_state = "MESHER"
                    
            if current_state == "MESHER":
                mesher.renderer.process_event(event)
                
                if mesher.finished:
                    solver = Solver(mesher.solver_data_pipeline(), [physicseditor.inlet_velocity,0.0],
                                    physicseditor.outlet_pressure,physicseditor.density,physicseditor.viscosity)

                    solver.Solve()
                    current_state = "SOLVER"
                
                


        # --- Fixed Update 
        while accumulator >= dt:
            accumulator -= dt

        # --- Render ---

        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)

        if current_state == "EDITOR":
            editor.draw(screen, camera)
        elif current_state == "PHYSICS":
            physicseditor.draw(screen,camera)
        elif current_state == "MESHER":
            mesher.draw(screen,camera)
        elif current_state == "SOLVER":
            mesher.draw(screen,camera)
        pygame.display.flip()

    pygame.quit()
    pass

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    
    run_app()
    
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('tottime')
    stats.print_stats(20) # Print the top 20 slowest functions