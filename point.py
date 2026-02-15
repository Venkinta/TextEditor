import numpy as np

class Point:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    # This allows set() and dict() to treat identical coordinates as the same key
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __repr__(self):
        return f"P({self.x}, {self.y})"
    
    def __sub__(self, other):
        if isinstance(other, Point):
            return np.array([self.x - other.x, self.y - other.y])
        return np.array([self.x - other[0], self.y - other[1]])

    def __add__(self, other):
        if isinstance(other, Point):
            return np.array([self.x + other.x, self.y + other.y])
        return np.array([self.x + other[0], self.y + other[1]])