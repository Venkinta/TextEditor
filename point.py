class Point:
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def draw(self, canvas, r=3, color='blue'):
        # Draw a small circle on the given canvas
        canvas.create_oval(self.x - r, self.y - r, self.x + r, self.y + r, fill=color)