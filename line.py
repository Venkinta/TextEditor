from point import Point
import pygame
from camera import Camera
import numpy as np

class Line:
    def __init__(self, a, b):
        # Convert to Point objects if they are passed as tuples/lists
        self.a = a if isinstance(a, Point) else Point(a[0], a[1])
        self.b = b if isinstance(b, Point) else Point(b[0], b[1])
        
        
        self.boundary_type = "Wall"
        self.u_val = 0.0
        self.v_val = 0.0
        self.p_val = 0.0
        
    def draw(self, screen, camera, color=(255, 255, 255), width=1):
        # Corrected method name
        camera.draw_line(screen, self, color, width)
        
    @property   
    def vector(self):
        # Now this safely works because self.a and self.b are Point objects
        return [self.b.x - self.a.x, self.b.y - self.a.y]
    
    def is_mouse_over(self, mouse_world_pos, threshold=5):
        # Vector from line start to line end (AB)
        # Vector from line start to mouse (AM)
        A = np.array([self.a.x, self.a.y])
        B = np.array([self.b.x, self.b.y])
        M = np.array([mouse_world_pos.x, mouse_world_pos.y])
        
        AB = B - A
        AM = M - A
        
        # Calculate the projection factor 't'
        # t = (AM dot AB) / |AB|^2
        line_mag_sq = np.dot(AB, AB)
        if line_mag_sq == 0: return False # Zero length line
        
        t = np.dot(AM, AB) / line_mag_sq
        
        # Clamp t to the range [0, 1] to stay on the segment
        t = max(0, min(1, t))
        
        # Find the nearest point on the segment
        nearest_point = A + t * AB
        
        # Calculate distance from mouse to nearest point
        distance = np.linalg.norm(M - nearest_point)
        
        return distance < threshold