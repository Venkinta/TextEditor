import pygame
import math
from line import Line
from point import Point
import pygame_widgets


class Quad:
    def __init__(self, p1, p2, p3, p4):
        # Stored in counter-clockwise order
        self.points = [p1, p2, p3, p4]

    def vertices(self):
        return self.points

    def edges(self):
        # A quad has 4 edges
        return [
            frozenset([self.points[0], self.points[1]]),
            frozenset([self.points[1], self.points[2]]),
            frozenset([self.points[2], self.points[3]]),
            frozenset([self.points[3], self.points[0]])
        ]
    
    def draw(self, screen):
        # Pygame can draw polygons easily
        coords = [(p.x, p.y) for p in self.points]
        pygame.draw.polygon(screen, (100, 255, 100), coords, 1) # Green for quads!