from triangulation import Triangulation
from triangle import Triangle
from point import Point
import inspect

def create_super_triangle(points):
    print("Called from:", inspect.stack()[1].function)
    minx = min(p.x for p in points)
    miny = min(p.y for p in points)

    maxx = max(p.x for p in points)
    maxy = max(p.y for p in points)


    pointa = Point(minx,miny)   #lower left
    pointb = Point(2 * maxx,miny)   #lower right
    pointc = Point(minx,2*maxy)   #upper left

    fiangle = Triangle(pointa,pointb,pointc)
    
    return fiangle
    

def orientCCW(triangle):
    a = triangle.a
    b = triangle.b
    c = triangle.c

    cross = (b.x - a.x)*(c.y - a.y) - (b.y - a.y)*(c.x - a.x)

    if cross < 0:
        # swap to make it CCW
        triangle.b, triangle.c = triangle.c, triangle.b

        
def checkCircumcentre(triangle,point):
    
    a = triangle.a
    b = triangle.b
    c = triangle.c
    d = point
    
    ax = a.x - d.x
    ay = a.y - d.y
    bx = b.x - d.x
    by = b.y - d.y
    cx = c.x - d.x
    cy = c.y - d.y

    det = ((
        (ax*ax + ay*ay) * (bx*cy - by*cx)
        - (bx*bx + by*by) * (ax*cy - ay*cx)
        + (cx*cx + cy*cy) * (ax*by - ay*bx)
    ) > 0) 

    return det
 

    
    