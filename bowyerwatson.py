import constructor as ct
from point import Point
from triangle import Triangle
from triangulation import Triangulation 
import numpy as np



def Bowyer_watson(input_points):
    # 1. Deduplicate points immediately
    points = list(set(input_points)) 
    
    triangulation = Triangulation()
    super_triangle = ct.create_super_triangle(points)
    triangulation.add_triangle(super_triangle)

    for point in points:
        badTriangles = []
        # Use edge_count to find edges that are NOT shared between bad triangles
        edge_count = {}

        for triangle in triangulation.triangles:
            if ct.checkCircumcentre(triangle, point):
                badTriangles.append(triangle)
                # Count occurrences of edges (frozensets are hashable)
                for edge in triangle.edges():
                    edge_count[edge] = edge_count.get(edge, 0) + 1

        # The hole's boundary consists of edges appearing exactly once
        polygon = [edge for edge, count in edge_count.items() if count == 1]

        # Remove bad triangles
        for t in badTriangles:
            triangulation.remove_triangle(t) # Assuming you have a remove method

        # Re-triangulate the hole
        for edge in polygon:
            # edge is a frozenset {PointA, PointB}
            v1, v2 = list(edge)
            newTriangle = Triangle(v1, v2, point)
            triangulation.add_triangle(newTriangle)

    # Cleanup: Remove triangles connected to the super-triangle vertices
    super_verts = set(super_triangle.vertices())
    triangulation.triangles = [
        t for t in triangulation.triangles 
        if not any(v in super_verts for v in t.vertices())
    ]

    return triangulation
