import numpy as np
from line import Line
from matplotlib.path import Path
import numpy as np
from bowyerwatson import Bowyer_watson
from point import Point
import pygame
import constructor as ct
from quad import Quad
from shapely.geometry import Polygon as ShapelyPoly
from shapely.geometry import Point as ShapelyPoint

import cProfile
import pstats



class Mesher:
    def __init__(self,screen,lines,n_layers,growth_factor,thickness,spacing,r):
        self.lines = lines
        self.points = None
        self.boundary_points = None
        self.candidate_points = None
        self.triangulation = None
        self.orientation = None
        self.thickness_mask = None
        
        
        #boundary_layers
        self.n_layers = n_layers 
        self.growth_factor = growth_factor
        self.thickness = thickness
        self.boundary_spacing = spacing
        
        #mesh generation
        self.r = r #20 is good
        
    def mesh(self):
        # 1. Get the lines in the correct loop order
        ordered_lines = self.build_polygon() 
        
        # 2. Calculate orientation (using the helper we wrote)
        # We pass a numpy array for speed
        vert_coords = [(line.a.x, line.a.y) for line in ordered_lines]
        vert_array = np.array(vert_coords)
        self.orientation = self.polygon_orientation(vert_array)

        # 3. Create high-res boundary points based on the ORDERED vertices
        # Now we have the ordered points and an array with their thicknesses
        self.create_boundary_points(ordered_lines) 
        
        # 4. Generate Layers
        layers = [self.boundary_points]

        
        for i in range(self.n_layers):
            current_factor_array = self.thickness_mask * self.thickness
            next_layer = self.boundary_layer(layers[-1], current_factor_array)
            layers.append(next_layer)
            self.thickness *= self.growth_factor # Geometric stretching
            

        # 5. Connect them into Quads
        self.boundary_elements = self.connect_layers(layers)

        # --- PHASE 2: Unstructured Interior ---
        # The last ring of the boundary layer is the "new" wall for the triangles
        inner_ring = layers[-1]
        
        # Generate Steiner points ONLY inside this inner ring
        self.create_steiner_points(inner_ring, self.r) 
        
        # Convert inner_ring and Steiner points to Point objects for Bowyer-Watson
        inner_ring_pts = [Point(p[0], p[1]) for p in inner_ring]
        steiner_pts = [Point(p[0], p[1]) for p in self.points]
        
        all_interior_pts = inner_ring_pts + steiner_pts
        
        # 4. Triangulate the core
        self.triangulation = Bowyer_watson(all_interior_pts)

        # 5. NEW: Filter out triangles that cross outside the inner ring
        self.filter_triangles(inner_ring)

        message = 'generated ' + repr(len(self.triangulation.triangles)) + ' cells'
        print(message)



        
        
    def create_boundary_points(self, ordered_lines):
        all_points = []
        all_thicknesses = []
        num_l = len(ordered_lines)

        for i in range(num_l):
            line = ordered_lines[i]
            # Wrap around for p2
            next_line = ordered_lines[(i + 1) % num_l]
            prev_line = ordered_lines[(i - 1) % num_l]
            
            start = np.array([line.a.x, line.a.y])
            end = np.array([next_line.a.x, next_line.a.y]) # Use the next line's start as our end

            line_vec = end - start
            line_length = np.linalg.norm(line_vec)
            if line_length == 0: continue

            n_points = max(1, int(np.floor(line_length / self.boundary_spacing)))
            segment_points = np.linspace(start, end, n_points, endpoint=False)
            all_points.append(segment_points)

            # DETERMINING THICKNESS
            # If this line is a wall, the whole segment is 4.
            # If the PREVIOUS line was a wall, the first point (the corner) should be 4.
            if line.boundary_type == "Wall":
                # (n_points, 1) ensures it plays nice with your coordinate math later
                seg_mask = np.ones((n_points,1))
            else:
                seg_mask = np.zeros((n_points,1))
            # 2. The Corner: Only the FIRST point of an inlet inherits the wall thickness
            
            if line.boundary_type != "Wall" and prev_line.boundary_type == "Wall":
                seg_mask[0] = 1.0

            all_thicknesses.append(seg_mask)
        
        self.boundary_points = np.vstack(all_points)
        # self.thickness_mask now holds our 1.0s and 0.0s
        self.thickness_mask = np.vstack(all_thicknesses)
        
        
        
        
    def check_points(self):
        #checks if generated points lie inside the boundary
        polygon_path = Path(self.boundary_points)  # your Nx2 array of vertices
        mask = polygon_path.contains_points(self.points)
        steiner_points = self.points[mask]  # only points truly inside polygon
      
      
      
        
    def create_steiner_points(self, boundary_points, r=550, k=30):
        
        
        if boundary_points is None or len(boundary_points) < 3:
            raise ValueError("Boundary polygon not defined properly.")


        
        full_poly = ShapelyPoly(boundary_points)
        safe_zone = full_poly.buffer(-r * 0.8)
        xmin, ymin, xmax, ymax = full_poly.bounds
        

        
        
        
        # --- SAFETY CHECK ---
        # If the grid is going to be massive, stop before we crash
        w = r / np.sqrt(2)
        cols = int(np.ceil((xmax - xmin) / w))
        rows = int(np.ceil((ymax - ymin) / w))
        
        
        if cols * rows > 500000: # Half a million cells limit
            
            print(f"Warning: Grid too dense ({cols}x{rows}). Increase 'r'.")
            self.points = np.array([])
            return


        grid = np.full((cols, rows), None, dtype=object)
        points = []
        active = []


        def get_grid_coords(p):
            gx = int((p[0] - xmin) / w)
            gy = int((p[1] - ymin) / w)
            return gx, gy



        # --- Step 1: Initial Point (with Safety) ---
        found_start = False
        attempts = 0
        
        while not found_start and attempts < 1000:
            
            attempts += 1
            p0 = np.random.uniform([xmin, ymin], [xmax, ymax])
            
            if safe_zone.contains(ShapelyPoint(p0)):
                
                points.append(p0)
                active.append(p0)
                gx, gy = get_grid_coords(p0)
                grid[gx, gy] = p0
                found_start = True
        
        if not found_start:
            print("Could not find a starting point inside the polygon!")
            self.points = np.array([])
            return

        # --- Step 2: Expansion ---
        while active:
            
            idx = np.random.randint(len(active))
            base_point = active[idx]
            found = False

            for _ in range(k):
                
                angle = np.random.uniform(0, 2 * np.pi)
                rad = np.random.uniform(r, 2 * r)
                candidate = base_point + rad * np.array([np.cos(angle), np.sin(angle)])

                # 1. Fast Bounding Box Check
                if not (xmin <= candidate[0] <= xmax and ymin <= candidate[1] <= ymax):
                    
                    continue
                
                # 2. Fast Grid Check (The "Secret Sauce")
                gx, gy = get_grid_coords(candidate)
                is_far_enough = True
                
                for i in range(max(0, gx - 2), min(cols, gx + 3)):
                    
                    for j in range(max(0, gy - 2), min(rows, gy + 3)):
                        
                        neighbor = grid[i, j]
                        
                        if neighbor is not None:
                            
                            if np.linalg.norm(candidate - neighbor) < r:
                                
                                is_far_enough = False
                                break
                            
                    if not is_far_enough: 
                        
                        break
                
                if not is_far_enough:
                    
                    continue

                # 3. Slow Polygon Check (ONLY do this if it passed everything else)
                
                if not safe_zone.contains(ShapelyPoint(candidate)):
                    continue

                # If we got here, the point is valid!
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

        ordered_lines = [first]
        pivot = first.b
        
        while remaining:

            found = False

            for i, line in enumerate(remaining):

                if np.array_equal(pivot,line.a):
                    pivot = line.b
                    ordered_lines.append(line)
                    remaining.pop(i)
                    found = True
                    break

                elif np.array_equal(pivot,line.b):
                    
                    pivot = line.a
                    ordered_lines.append(line)
                    remaining.pop(i)
                    found = True
                    break

            if not found:
                raise ValueError("Lines do not form a closed loop")


        return ordered_lines
  
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


    def draw(self, screen,camera):
        # --- Draw boundary lines ---
        if hasattr(self, "lines"):
            for line in self.lines:
                line.draw(screen,camera, color=(255, 255, 255), width=2)
                
        # Draw Boundary Layer Quads
        if hasattr(self, 'boundary_elements'):
            for quad in self.boundary_elements:
                quad.draw(screen,camera)

        # --- Draw triangulation ---
        if hasattr(self, "triangulation") and self.triangulation:
            self.triangulation.draw(screen,camera)
                    
    def create_boundary_layers(self, n_layers=1, scaling_factor=4):
        layers = [self.boundary_points]  # start with original
        for _ in range(n_layers):
            last_layer = layers[-1]
            new_layer = self.boundary_layer(last_layer, scaling_factor=scaling_factor)
            layers.append(new_layer)
        return layers

                        
                        
    def boundary_layer(self, polygon_points, scaling_factor):
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
                # Simple area check for a quad (sum of two triangles)
                # If the thickness was 0, p1==p4 and p2==p3, area will be 0.
                area = 0.5 * abs((p1.x*p2.y + p2.x*p3.y + p3.x*p4.y + p4.x*p1.y) - (p2.x*p1.y + p3.x*p2.y + p4.x*p3.y + p1.x*p4.y))
                            
                if area >1e-5:
                    new_quad = Quad(p1, p2, p3, p4)
                    elements.append(new_quad)
                
        return elements

  
    def _to_point(self, p):
        # Helper to handle the numpy vs Point confusion
        if isinstance(p, Point): return p
        return Point(p[0], p[1])
    
    def filter_triangles(self, inner_ring_points):
        """Removes triangles whose centroids fall outside the inner boundary ring."""
        # 1. Create a Path object from the inner ring
        ring_path = Path(inner_ring_points)
        
        # 2. Extract the centroids of all generated triangles
        centroids = [t.centroid for t in self.triangulation.triangles]
        
        # 3. Check which centroids are INSIDE the polygon ring
        # radius=-1e-5 adds a tiny tolerance so triangles right on the edge aren't deleted
        mask = ring_path.contains_points(centroids, radius=-1e-5)
        
        # 4. Rebuild the triangle list keeping only the valid ones
        valid_triangles = []
        for is_inside, triangle in zip(mask, self.triangulation.triangles):
            if is_inside:
                valid_triangles.append(triangle)
                
        # 5. Update the triangulation object
        self.triangulation.triangles = valid_triangles