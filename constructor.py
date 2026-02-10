import triangulation
import point
import triangle

def create_super_triangle(points):
    minx = min(points, key=lambda p: p.x)
    miny = min(points, key=lambda p: p.y)

    maxx = max(points, key=lambda p: p.x)
    maxy = max(points, key=lambda p: p.y)

    pointa = point(minx,miny)   #lower left
    pointb = point(2*maxx,miny)   #lower right
    pointc = point(minx,2*maxy)   #upper left

    super_triangle = triangle(pointa,pointb,pointc)