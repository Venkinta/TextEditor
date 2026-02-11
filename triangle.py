class Triangle:
    def __init__(self, a,b,c,neighbours=None):
        if neighbours is None:
            neighbours = []
        self.a = a
        self.b = b
        self.c = c
        self.neighbours = neighbours

