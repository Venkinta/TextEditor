class Solver:
    def __init__(self, mesher_data):
            
            'Nc': Nc, 
            'Nf': Nf,
            'owner': owner,
            'neighbor': neighbor,
            'Sf': Sf,
            'magSf': np.linalg.norm(Sf, axis=1), # Keep this for speed!
            'Cf': Cf,
            'df': df,
            'magDf': magDf,
            'cell_centers': cell_centers,
            'cell_areas': cell_areas,
            'boundary_tags': boundary_tags # The "Physics Key"
        
        pass