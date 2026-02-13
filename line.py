import pygame
class Line:
    def __init__(self,a,b):
        self.a = a
        self.b = b
        
    def draw(self,screen,color = (255, 255, 255), width = 4):

        pygame.draw.line(screen, color, self.a, self.b, width)
        