class SnapEngine:
    def __init__(self, pixel_radius=10):
        self.pixel_radius = pixel_radius

    # Inside snapengine.py

    def get_snapped_pos(self, current_world_pos, lines, camera_scale, anchor_pos=None):
        """
        Calculates the best snap position in World Coordinates.
        """
        # CHANGE THIS:
        wx = current_world_pos.x
        wy = current_world_pos.y
        
        # 1. Convert pixel sensitivity to world sensitivity
        world_radius = self.pixel_radius / camera_scale
        world_sq_radius = world_radius ** 2
        
        # --- Priority 1: Vertex Snapping ---
        for line in lines:
            for pt in [line.a, line.b]:
                # This is already safe because Line ensures pt is a Point
                px, py = pt.x, pt.y 
                
                dist_sq = (wx - px)**2 + (wy - py)**2
                if dist_sq <= world_sq_radius:
                    return pt # Return the actual Point object!

        # --- Priority 2: Axis Snapping ---
        if anchor_pos:
            # anchor_pos is also a Point now
            ax, ay = anchor_pos.x, anchor_pos.y
            
            if abs(wy - ay) < world_radius:
                wy = ay
            if abs(wx - ax) < world_radius:
                wx = ax

        # Return a new Point instead of a tuple to keep the system consistent
        from point import Point
        return Point(wx, wy)