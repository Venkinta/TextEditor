import imgui
from imgui.integrations.pygame import PygameRenderer
from line import Line

class PhysicsEditor:

    def __init__(self, screen, lines, renderer):
        self.lines = lines
        self.renderer = renderer # Use the passed-in global renderer
        self.finished = False
        self.density = 1.2
        self.viscosity = 0.0002
        self.selected_line = None
        self.boundary_types = ["Wall", "Velocity Inlet","Pressure Outlet"]
        self.current_line_idx = 0
        self.inlet_velocity = 1
        self.outlet_pressure = 0
        # REMOVE: imgui.create_context()
        # REMOVE: self.renderer = PygameRenderer()
        
        
        
        #boundary_layers
        self.n_layers = 4 
        self.growth_factor = 1.4
        self.thickness = 4
        self.boundary_spacing = 35
        
        #mesh generation
        self.r = 20 #20 is good

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
        
        opened, _ = imgui.collapsing_header("Boundary layer settings")
        
        if opened:
            
            changed,self.n_layers = imgui.input_int("N. Boundary layers", self.n_layers, step=1, step_fast=1) 
            changed,self.growth_factor = imgui.input_float("Growth factor", self.growth_factor, step=0.1, step_fast=1.0)
            changed,self.thickness = imgui.input_float("Thickness", self.thickness, step=0.1, step_fast=1.0)
            changed,self.boundary_spacing = imgui.input_float("Boundary cell spacing", self.boundary_spacing, step=0.1, step_fast=1.0)

        opened2, _ = imgui.collapsing_header("Mesher settings")
        
        if opened2:
            
            changed,self.r = imgui.input_float("Mesh size", self.r, step=0.1, step_fast=1.0) 

        
        if imgui.button("Proceed to Meshing"):
            self.finish()
        imgui.end()
        
        
        if self.selected_line:
            imgui.set_next_window_size(300, 90)
            imgui.set_next_window_position(10, 200)
            
            title = "Line " + str(self.lines.index(self.selected_line)+1) + " settings "
            self.current_line_idx = self.boundary_types.index(self.selected_line.boundary_type)
            
            imgui.begin(title)
            
            changed, self.current_line_idx = imgui.combo("Condition",self.current_line_idx,self.boundary_types)

            if self.selected_line.boundary_type == "Velocity Inlet":
                changed2,self.inlet_velocity = imgui.input_float("Inlet velocity", self.inlet_velocity,step = 0.1, step_fast = 1.0) 
            
            if self.selected_line.boundary_type == "Pressure Outlet":
                changed2,self.outlet_pressure = imgui.input_float("Outlet pressure", self.outlet_pressure,step = 0.1, step_fast = 1.0) 


            if changed:
                
                self.selected_line.boundary_type = self.boundary_types[self.current_line_idx]
                print(self.selected_line.boundary_type)
                
            imgui.end()

        # 4. Critical: "Stamp" the ImGui visuals onto the Pygame screen
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def handle_selection(self,pos):
        
        self.selected_line = None
        
        for line in self.lines:
            
            if line.is_mouse_over(pos):
                
                self.selected_line = line
                break
                
                
                
            
    def finish(self):
        self.finished = True
        pass