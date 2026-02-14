from triangulation import Triangulation
from triangle import Triangle
from point import Point
import inspect
import numpy as np 

def create_super_triangle(points):
    """Creates a triangle large enough to contain all points with massive padding."""
    min_x = min(p.x for p in points)
    max_x = max(p.x for p in points)
    min_y = min(p.y for p in points)
    max_y = max(p.y for p in points)

    dx = max_x - min_x
    dy = max_y - min_y
    dmax = max(dx, dy)
    mid_x = (min_x + max_x) / 2
    mid_y = (min_y + max_y) / 2

    # Scale factor 20 ensures the super-triangle doesn't cause precision issues
    # near the edges of your actual data.
    p1 = Point(mid_x - 20 * dmax, mid_y - dmax)
    p2 = Point(mid_x + 20 * dmax, mid_y - dmax)
    p3 = Point(mid_x, mid_y + 20 * dmax)

    return Triangle(p1, p2, p3)

def checkCircumcentre(triangle, point):
    """Standard determinant-based circumcircle check."""
    # Ensure CCW orientation for consistent results
    orientCCW(triangle)
    
    # Coordinates relative to the test point
    ax, ay = triangle.a.x - point.x, triangle.a.y - point.y
    bx, by = triangle.b.x - point.x, triangle.b.y - point.y
    cx, cy = triangle.c.x - point.x, triangle.c.y - point.y

    # Determinant of the 3x3 matrix (incircle test)
    det = (
        (ax*ax + ay*ay) * (bx*cy - cx*by) -
        (bx*bx + by*by) * (ax*cy - cx*ay) +
        (cx*cx + cy*cy) * (ax*by - bx*ay)
    )
    return det > 0   

def orientCCW(triangle):
    a = triangle.a
    b = triangle.b
    c = triangle.c

    cross = (b.x - a.x)*(c.y - a.y) - (b.y - a.y)*(c.x - a.x)

    if cross < 0:
        # swap to make it CCW
        triangle.b, triangle.c = triangle.c, triangle.b

        

 
def updatebadedges(edge_count, triangle):
    for edge in triangle.edges():
        edge_count[edge] = edge_count.get(edge, 0) + 1


    
    