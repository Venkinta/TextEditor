import imgui
from imgui.integrations.pygame import PygameRenderer

class PhysicsEditor:

    def __init__(self, screen, lines, renderer):
        self.lines = lines
        self.renderer = renderer # Use the passed-in global renderer
        self.finished = False
        self.density = 0.0
        self.viscosity = 0.0
        # REMOVE: imgui.create_context()
        # REMOVE: self.renderer = PygameRenderer()

    def draw(self, screen, camera):
        # 2. Tell ImGui a new frame is starting
        imgui.new_frame()

        # Draw the lines underneath
        for line in self.lines:
            line.draw(screen, camera)

        # 3. Define the UI
        imgui.begin("Mesher Settings")
        changed, self.density = imgui.input_float("Density (rho)", self.density, step=0.1, step_fast=1.0)
        changed, self.viscosity = imgui.input_float("Viscosity (mu)", self.viscosity, step=0.1, step_fast=1.0)
        
        if imgui.button("Proceed to Meshing"):
            self.finish()
        imgui.end()

        # 4. Critical: "Stamp" the ImGui visuals onto the Pygame screen
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

            
            
    def finish(self):
        self.finished = True
        pass