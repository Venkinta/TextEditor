from point import Point
import pygame
from camera import Camera

class Line:
    def __init__(self, a, b):
        # Convert to Point objects if they are passed as tuples/lists
        self.a = a if isinstance(a, Point) else Point(a[0], a[1])
        self.b = b if isinstance(b, Point) else Point(b[0], b[1])
        
    def draw(self, screen, camera, color=(255, 255, 255), width=1):
        # Corrected method name
        camera.draw_line(screen, self, color, width)
        
    @property   
    def vector(self):
        # Now this safely works because self.a and self.b are Point objects
        return [self.b.x - self.a.x, self.b.y - self.a.y]