import constructor
from point import Point
import triangle
import triangulation
import numpy as np
import tkinter as tk  # always standard to alias as tk


class MyCanvas(tk.Canvas):
    def draw(self, objects):
        for obj in objects:
            if hasattr(obj, 'draw'):
                obj.draw(self)


root = tk.Tk()  # this creates the application window
root.title("My First GUI")  # optional, just sets the window title
root.geometry("120x120")   # optional, width x height
canvas = MyCanvas(root, width=120, height=120, background='white')


points = []
points = [Point(*np.random.randint(100, size=2)) for _ in range(30)]

canvas.pack()
canvas.draw(points)


root.mainloop()