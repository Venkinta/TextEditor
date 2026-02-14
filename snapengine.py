
import pygame
import math
from line import Line


class SnapEngine:
    def __init__(self, pixel_radius=10):
        self.radius = pixel_radius
        self.sq_radius = pixel_radius ** 2

    def get_snapped_pos(self, current_pos, lines, anchor_pos=None):
        """
        Calculates the best snap position.
        1. Checks for Vertex Snaps (endpoints of existing lines).
        2. If no vertex snap and anchor_pos exists, checks Axis Snaps (H/V).
        """
        x, y = current_pos
        
        # --- Priority 1: Vertex Snapping (Snap to existing points) ---
        for line in lines:
            # Check both start (a) and end (b) of every line
            for pt in [line.a, line.b]:
                # Assuming pt is (x, y) or has .x .y
                px, py = pt if isinstance(pt, tuple) else (pt.x, pt.y)
                
                dist_sq = (x - px)**2 + (y - py)**2
                if dist_sq <= self.sq_radius:
                    return (px, py) # Return immediately on first snap

        # --- Priority 2: Axis Snapping (Horizontal/Vertical) ---
        # Only happens if we have a starting point (anchor_pos)
        if anchor_pos:
            ax, ay = anchor_pos
            
            # Snap Y (Horizontal line)
            if abs(y - ay) < self.radius:
                y = ay
            # Snap X (Vertical line)
            if abs(x - ax) < self.radius:
                x = ax

        return (x, y)