import numpy as np
from line import Line
from matplotlib.path import Path

class Mesher:
    def __init__(self,lines):
        self.lines = lines
        self.points = None
        self.boundary_points = None
        self.candidate_points = None
        
        
        
    def create_boundary_points(self):
        all_points = []

        for line in self.lines:
            start = np.array(line.a)
            end = np.array(line.b)
            spacing = 10.0

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
        mask = polygon_path.contains_points(candidate_points)
        steiner_points = candidate_points[mask]  # only points truly inside polygon
        
        