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
    edge_count = {}
    for triangle in triangulation.triangles:
        ct.orientCCW(triangle)
        if ct.checkCircumcentre(triangle, point):
            badTriangles.append(triangle)
            ct.updatebadedges(edge_count,triangle)
            
    polygon = []
    for triangle in badTriangles:
        for edge in triangle.edges():
            if edge_count.get(edge,0) == 1: # edge is shared by more than one bad triangle
                polygon.append(edge)
                
    bad_set = set(badTriangles)
    triangulation.triangles = [t for t in triangulation.triangles if t not in bad_set]
    
    for edge in polygon:
        newTriangle = Triangle(*edge, point)
        triangulation.add_triangle(newTriangle)
        
super_vertices = {*super_triangle.vertices()}
triangulation.triangles = [t for t in triangulation.triangles if not any(v in super_vertices for v in t.vertices())]
    
    
    
        
                    
