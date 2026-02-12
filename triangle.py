class Triangle:
    def __init__(self, a,b,c,neighbours=None):
        if neighbours is None:
            neighbours = []
        self.a = a
        self.b = b
        self.c = c
        self.neighbours = neighbours
        
    def vertices(self):
        return self.a,self.b,self.c
        
    def edges(self):
        return [
            frozenset((self.a, self.b)),
            frozenset((self.b, self.c)),
            frozenset((self.c, self.a)),
        ]

