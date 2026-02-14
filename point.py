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