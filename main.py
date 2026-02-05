import tkinter as tk  # common alias
from tkinter import *
from tkinter import ttk
from cursor import cursor

root = tk.Tk()  # create the main window
root.title("My App")
root.geometry("400x300")  # width x height
canvas = Canvas(root, width = 500, height = 400, background='gray75')

canvas.create_text(130, 100, text='A', anchor='nw', font='TkMenuFont', fill='red')
pointer = cursor(width = 10, height = 50)
pointer.draw(canvas =canvas ,xo=100,yo=100)

canvas.pack(fill="both", expand=True)
root.mainloop()  # starts the event loop

