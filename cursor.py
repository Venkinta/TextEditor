import tkinter

class cursor():
    def __init__(self,*, width = 3, height = 10,on=False):
        self.width = width
        self.height = height
        self.on = on

    def draw(self, canvas, xo,yo):
        if self.on:
            canvas.create_rectangle(xo,yo,  xo+self.width, yo+self.height, fill='black')
            self.on = False
        elif not self.on:
            canvas.create_rectangle(xo,yo,  xo+self.width, yo+self.height, fill='grey')   
            self.on = True 
        
        
        