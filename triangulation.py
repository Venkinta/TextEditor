class Triangulation:
    def __init__(self,triangles=None):
        if triangles is None:
            triangles = []
        self.triangles = triangles
    def add_triangle(self,triangle):    
        self.triangles.append(triangle)