import constructor as ct
from point import Point
from triangle import Triangle
from triangulation import Triangulation 
import numpy as np



points = []
points = [Point(*np.random.randint(100, size=2)) for _ in range(30)]

triangulation = Triangulation()


#add super triangle
super_triangle = ct.create_super_triangle(points)

triangulation.add_triangle(super_triangle)



for point in points:
    badTriangles = []
    for triangle in triangulation.triangles:
        ct.orientCCW(triangle)
        
