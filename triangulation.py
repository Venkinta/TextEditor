class Triangulation:
    def __init__(self, triangles=None):
        if triangles is None:
            triangles = []
        self.triangles = triangles

    def add_triangle(self, triangle):    
        self.triangles.append(triangle)

    def remove_triangle(self, triangle):
        # We use a try/except because if the triangle isn't there, 
        # we don't want the whole mesher to crash.
        try:
            self.triangles.remove(triangle)
        except ValueError:
            pass