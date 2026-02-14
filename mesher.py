import numpy as np
from line import Line
from matplotlib.path import Path
import numpy as np
from bowyerwatson import Bowyer_watson
from point import Point
import pygame
from shapely.geometry import Polygon

import cProfile
import pstats



class Mesher:
    def __init__(self,screen,lines):
        self.lines = lines
        self.points = None
        self.boundary_points = None
        self.candidate_points = None
        self.triangulation = None
        
    def mesh(self):
        profiler = cProfile.Profile()
        profiler.enable()

        self.boundary_points = self.build_polygon() #Orders the boundary vertices and returns an array of points
        self.create_steiner_points() #returns the steiner points to self.points
        self.create_boundary_points() #this overwrites the previous self.boundary_points and interpolates between the vertices
        joined_points = np.vstack([self.points, self.boundary_points])
        joined_points_pts = [Point(x, y) for x, y in joined_points]
        
        self.triangulation = Bowyer_watson(joined_points_pts)
        
        
        #-------------DEBUGGGING-------------
        #-------------DEBUGGGING-------------
        #-------------DEBUGGGING-------------
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats("cumulative")
        stats.print_stats(20)  # print top 20 time-consuming calls
        
        all_points = joined_points_pts
        seen = set()
        duplicates = 0
        for p in all_points:
            tup = (p.x, p.y)
            if tup in seen:
                duplicates += 1
            seen.add(tup)
        print(f"Duplicate points: {duplicates}")
        
        edge_lengths = []
        for t in self.triangulation.triangles:
            verts = [t.a, t.b, t.c]
            for i in range(3):
                dx = verts[i].x - verts[(i+1)%3].x
                dy = verts[i].y - verts[(i+1)%3].y
                edge_lengths.append(np.hypot(dx, dy))

        print(f"Edge lengths: min={min(edge_lengths)}, max={max(edge_lengths)}, mean={np.mean(edge_lengths)}")
        def check_intersections(triangles):
            polys = [Polygon([(t.a.x,t.a.y),(t.b.x,t.b.y),(t.c.x,t.c.y)]) for t in triangles]
            intersections = 0
            for i, p1 in enumerate(polys):
                for j, p2 in enumerate(polys):
                    if j <= i:
                        continue
                    if p1.intersects(p2):
                        intersections += 1
                        if intersections <= 10:
                            print(f"Triangles {i} and {j} intersect!")
            print(f"Total intersecting pairs: {intersections}")

        check_intersections(self.triangulation.triangles)
        #-------------DEBUGGGING-------------
        #-------------DEBUGGGING-------------
        #-------------DEBUGGGING-------------

        
        
        
        
    def create_boundary_points(self):
        all_points = []

        for line in self.lines:
            start = np.array(line.a)
            end = np.array(line.b)
            spacing = 45

            line_vec = end - start
            line_length = np.linalg.norm(line_vec)

            if line_length == 0:  # skip degenerate lines
                continue

            n_points = int(np.floor(line_length / spacing)) + 1
            unit_dir = line_vec / line_length

            points = [start + i * spacing * unit_dir for i in range(n_points)]
            points.append(end)  # ensure end is included

            all_points.extend(points)

        all_points = np.array(all_points)
        self.boundary_points = all_points
        
    def check_points(self):
        #checks if generated points lie inside the boundary
        polygon_path = Path(self.boundary_points)  # your Nx2 array of vertices
        mask = polygon_path.contains_points(self.points)
        steiner_points = self.points[mask]  # only points truly inside polygon
        
    def create_steiner_points(self, r=15.0, k=30):
        if self.boundary_points is None or len(self.boundary_points) < 3:
            raise ValueError("Boundary polygon not defined properly.")

        polygon = Path(self.boundary_points)
        
        # 1. Bounding box & Grid Setup
        xmin, ymin = np.min(self.boundary_points, axis=0)
        xmax, ymax = np.max(self.boundary_points, axis=0)
        
        w = r / np.sqrt(2)  # Cell size
        cols = int(np.ceil((xmax - xmin) / w))
        rows = int(np.ceil((ymax - ymin) / w))
        
        # Grid stores the actual point [x, y] or None
        grid = np.full((cols, rows), None, dtype=object)

        points = []
        active = []

        def get_grid_coords(p):
            grid_x = int((p[0] - xmin) / w)
            grid_y = int((p[1] - ymin) / w)
            return grid_x, grid_y

        # --- Step 1: Initial random point ---
        found_start = False
        while not found_start:
            p0 = np.random.uniform([xmin, ymin], [xmax, ymax])
            if polygon.contains_point(p0):
                points.append(p0)
                active.append(p0)
                gx, gy = get_grid_coords(p0)
                grid[gx, gy] = p0
                found_start = True

        # --- Step 2: Expansion ---
        while active:
            idx = np.random.randint(len(active))
            base_point = active[idx]
            found = False

            for _ in range(k):
                angle = np.random.uniform(0, 2 * np.pi)
                radius = np.random.uniform(r, 2 * r)
                candidate = base_point + radius * np.array([np.cos(angle), np.sin(angle)])

                # Boundary Check
                if not (xmin <= candidate[0] <= xmax and ymin <= candidate[1] <= ymax):
                    continue
                if not polygon.contains_point(candidate):
                    continue

                # Grid Check (The "Secret Sauce")
                gx, gy = get_grid_coords(candidate)
                
                # Check 5x5 neighborhood
                is_far_enough = True
                for i in range(max(0, gx - 2), min(cols, gx + 3)):
                    for j in range(max(0, gy - 2), min(rows, gy + 3)):
                        neighbor = grid[i, j]
                        if neighbor is not None:
                            if np.linalg.norm(candidate - neighbor) < r:
                                is_far_enough = False
                                break
                    if not is_far_enough: break

                if is_far_enough:
                    points.append(candidate)
                    active.append(candidate)
                    grid[gx, gy] = candidate
                    found = True
                    break

            if not found:
                active.pop(idx)

        self.points = np.array(points)

    def build_polygon(self):

        remaining = self.lines.copy()

        first = remaining.pop(0)

        start = first.a
        pivot = first.b

        polygon = [start, pivot]

        while remaining:

            found = False

            for i, line in enumerate(remaining):

                if pivot == line.a:
                    pivot = line.b
                    polygon.append(pivot)
                    remaining.pop(i)
                    found = True
                    break

                elif pivot == line.b:
                    pivot = line.a
                    polygon.append(pivot)
                    remaining.pop(i)
                    found = True
                    break

            if not found:
                raise ValueError("Lines do not form a closed loop")

            if pivot == start:
                break

        return polygon

    def draw(self, screen):
        # --- Draw boundary lines ---
        if hasattr(self, "lines"):
            for line in self.lines:
                line.draw(screen, color=(255, 255, 255), width=2)

        # --- Draw triangulation ---
        if hasattr(self, "triangulation") and self.triangulation:
            for triangle in self.triangulation.triangles:
                # Draw edges of the triangle
                edges = triangle.edges()
                for edge in edges:
                    # edge is a frozenset of Points
                    a, b = tuple(edge)
                    pygame.draw.line(
                        screen,
                        (100, 200, 255),  # light blue for triangles
                        (a.x, a.y),
                        (b.x, b.y),
                        1
                    )

                    