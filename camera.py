import pygame

class Camera:
    def __init__(self, scale=1.0, offset=None):
        self.scale = scale
        self.offset = offset if offset is not None else [0.0, 0.0]

    def to_screen(self, world_point):
        """Helper to convert a Point or [x,y] to Screen Pixels."""
        # Handle both Point objects and raw lists/tuples
        px = world_point.x if hasattr(world_point, 'x') else world_point[0]
        py = world_point.y if hasattr(world_point, 'y') else world_point[1]
        
        sx = (px + self.offset[0]) * self.scale
        sy = (py + self.offset[1]) * self.scale
        return (sx, sy)

    def screen_to_world(self, screen_pos):
        """Inverse: Pixels to World Meters."""
        sx, sy = screen_pos
        wx = (sx / self.scale) - self.offset[0]
        wy = (sy / self.scale) - self.offset[1]
        from point import Point 
        return Point(wx, wy)

    def handle_zoom(self, mouse_pos, scroll_y):
        mx, my = mouse_pos
        zoom_factor = 1.1 if scroll_y > 0 else 0.9
        
        # Adjust offset to keep mouse point anchored
        self.offset[0] = mx / (self.scale * zoom_factor) - (mx / self.scale - self.offset[0])
        self.offset[1] = my / (self.scale * zoom_factor) - (my / self.scale - self.offset[1])
        
        self.scale *= zoom_factor

    def draw_line(self, screen, line, color, width):
        p0 = self.to_screen(line.a)
        p1 = self.to_screen(line.b)
        pygame.draw.line(screen, color, p0, p1, width)

    def draw_polygon(self, polygon_vertices, screen, color, width):
        # We create a NEW list of screen points so we don't 
        # accidentally overwrite the triangle's actual data
        screen_points = [self.to_screen(p) for p in polygon_vertices]

        pygame.draw.polygon(screen, color, screen_points, width)