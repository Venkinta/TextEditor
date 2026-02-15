import numpy as np
from line import Line
from matplotlib.path import Path
import numpy as np
from bowyerwatson import Bowyer_watson
from point import Point
import pygame
from shapely.geometry import Polygon
import constructor as ct
from quad import Quad

import cProfile
import pstats



class Mesher:
    def __init__(self,screen,lines):
        self.lines = lines
        self.points = None
        self.boundary_points = None
        self.candidate_points = None
        self.triangulation = None
        self.orientation = None
        
    def mesh(self):
        # 1. Get the vertices in the correct loop order
        ordered_verts = self.build_polygon() 
        
        # 2. Calculate orientation (using the helper we wrote)
        # We pass a numpy array for speed
        vert_array = np.array([(p.x, p.y) for p in ordered_verts])
        self.orientation = self.polygon_orientation(vert_array)

        # 3. Create high-res boundary points based on the ORDERED vertices
        self.create_boundary_points(ordered_verts) 
        
        # 4. Generate Layers
        layers = [self.boundary_points]
        n_layers = 3
        growth_factor = 1.2
        thickness = 6
        
        for i in range(n_layers):
            next_layer = self.boundary_layer(layers[-1], scaling_factor=thickness)
            layers.append(next_layer)
            thickness *= growth_factor # Geometric stretching

        # 5. Connect them into Quads
        self.boundary_elements = self.connect_layers(layers)

        # --- PHASE 2: Unstructured Interior ---
        # The last ring of the boundary layer is the "new" wall for the triangles
        inner_ring = layers[-1]
        
        # Generate Steiner points ONLY inside this inner ring
        self.create_steiner_points(inner_ring, r=20.0) 
        
        # Convert inner_ring and Steiner points to Point objects for Bowyer-Watson
        inner_ring_pts = [Point(p[0], p[1]) for p in inner_ring]
        steiner_pts = [Point(p[0], p[1]) for p in self.points]
        
        all_interior_pts = inner_ring_pts + steiner_pts
        
        # 4. Triangulate the core
        self.triangulation = Bowyer_watson(all_interior_pts)



        
        
    def create_boundary_points(self, ordered_vertices):
        all_points = []
        spacing = 45

        for i in range(len(ordered_vertices)):
            # Get the current segment (p1 to p2)
            p1 = ordered_vertices[i]
            p2 = ordered_vertices[(i + 1) % len(ordered_vertices)]
            
            start = np.array([p1.x, p1.y])
            end = np.array([p2.x, p2.y])

            line_vec = end - start
            line_length = np.linalg.norm(line_vec)

            if line_length == 0: continue

            n_points = max(1, int(np.floor(line_length / spacing)))
            # We use linspace to avoid accumulation errors and ensure start/end alignment
            segment_points = np.linspace(start, end, n_points, endpoint=False)
            all_points.append(segment_points)

        self.boundary_points = np.vstack(all_points)
        
    def check_points(self):
        #checks if generated points lie inside the boundary
        polygon_path = Path(self.boundary_points)  # your Nx2 array of vertices
        mask = polygon_path.contains_points(self.points)
        steiner_points = self.points[mask]  # only points truly inside polygon
        
    def create_steiner_points(self, boundary_points, r=15.0, k=30):
        if boundary_points is None or len(boundary_points) < 3:
            raise ValueError("Boundary polygon not defined properly.")

        polygon = Path(boundary_points)
        
        # 1. Bounding box & Grid Setup
        xmin, ymin = np.min(boundary_points, axis=0)
        xmax, ymax = np.max(boundary_points, axis=0)
        
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
  
    def polygon_orientation(self, polygon_array):
        """
        polygon_array: Nx2 numpy array
        """
        x = polygon_array[:, 0]
        y = polygon_array[:, 1]
        
        # Shoelace formula using numpy roll for the (i+1) terms
        # sum of (x_i * y_{i+1} - x_{i+1} * y_i)
        area = np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
        return area # area < 0 is CCW, area > 0 is CW


    def draw(self, screen):
        # --- Draw boundary lines ---
        if hasattr(self, "lines"):
            for line in self.lines:
                line.draw(screen, color=(255, 255, 255), width=2)
                
        # Draw Boundary Layer Quads
        if hasattr(self, 'boundary_elements'):
            for quad in self.boundary_elements:
                quad.draw(screen)

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
                    
    def create_boundary_layers(self, n_layers=1, scaling_factor=4):
        layers = [self.boundary_points]  # start with original
        for _ in range(n_layers):
            last_layer = layers[-1]
            new_layer = self.boundary_layer(last_layer, scaling_factor=scaling_factor)
            layers.append(new_layer)
        return layers

                        
                        
    def boundary_layer(self, polygon_points, scaling_factor=4):
        """
        polygon_points: np.array of shape (N, 2)
        Returns: np.array of shape (N, 2) representing the offset ring
        """
        n = len(polygon_points)
        new_points = np.zeros_like(polygon_points)

        # 1. Get edge vectors and their unit normals
        # We use roll to get the "next" point for each edge
        next_points = np.roll(polygon_points, -1, axis=0)
        edges = next_points - polygon_points
        edge_lengths = np.linalg.norm(edges, axis=1)[:, np.newaxis]
        unit_edges = edges / edge_lengths

        # Normals (perpendicular to edges)
        # If CCW: normal is (-dy, dx)
        if self.orientation > 0:
            edge_normals = np.column_stack([-unit_edges[:, 1], unit_edges[:, 0]])
        else:
            edge_normals = np.column_stack([unit_edges[:, 1], -unit_edges[:, 0]])

        # 2. Calculate vertex normals (Miter vectors)
        # The vertex normal is the average of the normals of the two meeting edges
        prev_edge_normals = np.roll(edge_normals, 1, axis=0)
        vertex_normals = prev_edge_normals + edge_normals
        
        # Normalize the vertex normal
        v_norm = np.linalg.norm(vertex_normals, axis=1)[:, np.newaxis]
        # Handle collinear edges to avoid division by zero
        vertex_normals = np.where(v_norm > 1e-9, vertex_normals / v_norm, edge_normals)

        # 3. Calculate Miter Length
        # The length needs to be adjusted so the perpendicular distance remains 'scaling_factor'
        # Length = scaling_factor / cos(theta), where 2*theta is the angle between edges
        # cos(theta) is the dot product of vertex_normal and edge_normal
        cos_theta = np.sum(vertex_normals * edge_normals, axis=1)[:, np.newaxis]
        miter_length = scaling_factor / np.maximum(cos_theta, 0.1) # Clamp to avoid blow-up at sharp spikes

        new_points = polygon_points + vertex_normals * miter_length
        
        return new_points

    def connect_layers(self, layers):
        """
        Connects concentric rings of points into Quad elements.
        layers: list of lists (or arrays) of points.
        """
        elements = []
        
        # Iterate through each gap between layers
        for i in range(len(layers) - 1):
            current_layer = layers[i]
            next_layer = layers[i + 1]
            
            # We assume layers have matching point counts
            num_points = len(current_layer)
            
            for j in range(num_points):
                # Get indices, wrapping around for the last segment
                j_next = (j + 1) % num_points
                
                # Get the 4 corners of the quad
                # Note: Convert to Point object if they are currently numpy arrays
                p1 = self._to_point(current_layer[j])
                p2 = self._to_point(current_layer[j_next])
                p3 = self._to_point(next_layer[j_next])
                p4 = self._to_point(next_layer[j])
                
                # Create a Quad
                new_quad = Quad(p1, p2, p3, p4)
                elements.append(new_quad)
                
        return elements

    def _to_point(self, p):
        # Helper to handle the numpy vs Point confusion
        if isinstance(p, Point): return p
        return Point(p[0], p[1])