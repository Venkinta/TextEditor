import numpy as np

class Solver:
    def __init__(self, mesher_data, inlet_velocity, outlet_pressure, rho, viscosity):
        # Store fluid properties and BCs
        self.inlet_velocity = inlet_velocity
        self.outlet_pressure = outlet_pressure
        self.rho = rho
        self.viscosity = viscosity
        
        # Unpack mesh dictionary
        mesh = mesher_data
        self.Nc = mesh['Nc']
        self.Nf = mesh['Nf']
        
        # Topology arrays (1-D int)
        self.owner = mesh['owner']
        self.neighbor = mesh['neighbor']
        self.boundary_tags = mesh['boundary_tags']
        
        # Geometry arrays (2-D or 1-D float)
        self.Sf = mesh['Sf']
        self.magSf = mesh['magSf']
        self.Cf = mesh['Cf']
        self.df = mesh['df']
        self.magDf = mesh['magDf']
        
        # Cell geometry
        self.cell_centers = mesh['cell_centers']
        self.cell_areas = mesh['cell_areas']
        
        
        """
            'Nc': Nc, #number of cells
            'Nf': Nf, #number of faces
            'owner': owner, #each face has an owner ID
            'neighbor': neighbor, #each face has a neighbour ID
            'Sf': Sf, #face normal vector
            'magSf': np.linalg.norm(Sf, axis=1), # face normal vector magnitude
            'Cf': Cf, #center of face 
            'df': df, #vector from owner to neighbour
            'magDf': magDf, #magnitude of vector (distance)
            'cell_centers': cell_centers, #center of each cell
            'cell_areas': cell_areas, #area of each cell
            'boundary_tags': boundary_tags # Tag of each face type -1: Internal, 0: Wall, 1: Inlet, 2: Outlet
        """
    
    def initialize_conditions(self):

        p = np.ones(self.Nc)*self.outlet_pressure
        u = np.ones(self.Nc,2)*self.inlet_velocity *0.6
         
        """wall_faces = np.where(self.boundary_tags == 0)[0]
        inlet_faces = np.where(self.boundary_tags == 1)[0]
        outlet_faces = np.where(self.boundary_tags == 2)[0]
        internal_faces = np.where(self.boundary_tags == -1)[0]  # optional


        self.U[self.owner[inlet_faces], :] = self.inlet_velocity
        self.U[self.owner[wall_faces],:] = 0
        self.p[self.owner[outlet_faces]]"""

        



    def SIMPLE_UPDATE_FACE_FLUX(self):
        pass