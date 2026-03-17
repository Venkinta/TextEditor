import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve


class Solver:
    def __init__(self, mesher_data, inlet_velocity, outlet_pressure, rho, viscosity):
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
        
        
        ###############
        
        self.wall_faces = np.where(self.boundary_tags == 0)[0]
        self.inlet_faces = np.where(self.boundary_tags == 1)[0]
        self.outlet_faces = np.where(self.boundary_tags == 2)[0]
        self.internal_faces = np.where(self.boundary_tags == -1)[0] #returns array of the indices where wall faces, inlet faces, outlet faces... are
        

    def Solve(self, max_iterations=1000, tolerance=1e-6):
        """
        SIMPLE algorithm main loop
        """
        
        self.initialize_conditions()
        
        initial_residuals = None
    
        for iteration in range(max_iterations):
            
            self.U_old = self.U.copy()
            
            # Step 1: Update fluxes
            self.SIMPLE_UPDATE_FACE_FLUX_AND_DIFFUSSION()
            
            # Step 2: Assemble and solve momentum
            A_x, b_x, a_P_u = self.assemble_momentum(axis=0)
            A_y, b_y, a_P_v = self.assemble_momentum(axis=1)
            
            u_star, v_star = self.GET_VAR_STAR(A_x, b_x, A_y, b_y)
            
            # Step 3: Assemble and solve pressure correction
            A_p, b_p = self.ASSEMBLE_PRESSURE_CORRECTION(a_P_u, a_P_v)
            p_prime = self.GET_VAR_CORRECTED(A_p, b_p)
            
            # Step 4: Correct pressure and velocity
            self.CORRECT_PRESSURE_AND_VELOCITY(p_prime, a_P_u, a_P_v, u_star, v_star)
            
            # Step 5: Check convergence
            residual_continuity = np.linalg.norm(b_p)
            residual_u = np.linalg.norm(A_x @ self.U[:, 0] - b_x)
            residual_v = np.linalg.norm(A_y @ self.U[:, 1] - b_y)
            
            # Store initial residuals
            if iteration == 0:
                initial_residuals = {
                    'cont': max(residual_continuity, 1e-10),
                    'u': max(residual_u, 1e-10),
                    'v': max(residual_v, 1e-10)
                }
            
            # Normalize by initial values
            norm_cont = residual_continuity / initial_residuals['cont']
            norm_u = residual_u / initial_residuals['u']
            norm_v = residual_v / initial_residuals['v']
            
            max_residual = max(norm_cont, norm_u, norm_v)
            
            if iteration % 10 == 0:
                print(f"Iteration {iteration}: "
                    f"Cont = {norm_cont:.2e}, "
                    f"U = {norm_u:.2e}, "
                    f"V = {norm_v:.2e}")
            
            if max_residual < tolerance:
                print(f"\n✓ Converged!")
                break
        else:
            print(f"\n⚠ Did not converge in {max_iterations} iterations")
            print(f"Final residuals: {max_residual:.2e}")

        
    
    def initialize_conditions(self):
        # Your current code:
        self.P = np.ones((self.Nc)) * self.outlet_pressure
        
        # Better: Set a gradient from inlet to outlet
        # This gives the solver a better starting point
        
        # Find inlet and outlet cell centers
        inlet_cells = self.owner[self.inlet_faces]
        outlet_cells = self.owner[self.outlet_faces]
        
        # Calculate a rough pressure gradient
        # (This is just an initial guess, solver will correct it)
        x_coords = self.cell_centers[:, 0]
        x_min, x_max = x_coords.min(), x_coords.max()
        
        # Linear pressure drop from inlet to outlet
        self.P = self.outlet_pressure + (x_max - x_coords) / (x_max - x_min) * 10.0
        
        self.U = np.ones((self.Nc, 2)) * self.inlet_velocity * 0.6
        
        # Face mass flux
        self.phi = np.zeros(self.Nf)
        self.diff = np.zeros(self.Nf)
        



    def SIMPLE_UPDATE_FACE_FLUX_AND_DIFFUSSION(self):
        
        owner = self.owner[self.internal_faces]
        neighbor = self.neighbor[self.internal_faces]
        U_interp = (self.U[owner] + self.U[neighbor])/2 # IMPORTANT: DECISION TO USE CENTRAL DIFFERENCING
        
        
        
        self.phi[self.internal_faces] = self.rho * np.sum(U_interp * self.Sf[self.internal_faces],axis=1) #phi[f] = rho * u_face · n_face * |Sf|
        
        self.phi[self.inlet_faces] = self.rho * np.sum(self.inlet_velocity * self.Sf[self.inlet_faces],axis=1)
        
        self.phi[self.outlet_faces] = self.rho * np.sum(self.U[self.owner[self.outlet_faces]] * self.Sf[self.outlet_faces],axis=1)
        
        self.phi[self.wall_faces] = 0 # redundancy
        
        
        

        self.diff[self.internal_faces] = self.viscosity * (self.magSf[self.internal_faces])/(self.magDf[self.internal_faces])
        
        self.diff[self.inlet_faces] = self.viscosity * (self.magSf[self.inlet_faces])/(self.magDf[self.inlet_faces])
        
        self.diff[self.outlet_faces] = 0
        
        self.diff[self.wall_faces] = self.viscosity * (self.magSf[self.wall_faces])/(self.magDf[self.wall_faces])
        
        
    
    def assemble_momentum(self, axis):
        A = lil_matrix((self.Nc, self.Nc))
        b = np.zeros(self.Nc)
        
        # --- 1. INTERNAL FACES ---
        f_int = self.internal_faces
        own_i = self.owner[f_int]
        nei_i = self.neighbor[f_int]
        
        F = self.phi[f_int]
        D = self.diff[f_int]
        
        pos = F >= 0
        neg = ~pos
        
        # Owner/Neighbor contributions (Upwind + Diffusion)
        A[own_i[pos], own_i[pos]] += F[pos] + D[pos]
        A[own_i[pos], nei_i[pos]] += -D[pos]
        A[nei_i[pos], nei_i[pos]] += D[pos]
        A[nei_i[pos], own_i[pos]] += -F[pos] - D[pos]

        A[own_i[neg], own_i[neg]] += D[neg]
        A[own_i[neg], nei_i[neg]] += -D[neg] - F[neg]
        A[nei_i[neg], nei_i[neg]] += -F[neg] + D[neg]
        A[nei_i[neg], own_i[neg]] += -D[neg]
        
        # --- 2. BOUNDARY FACES ---
        # Inlet
        f_in = self.inlet_faces
        own_in = self.owner[f_in]
        A[own_in, own_in] += self.diff[f_in]
        b[own_in] += self.diff[f_in] * self.inlet_velocity[axis]
        
        # Wall (No-slip: b += 0)
        f_w = self.wall_faces
        own_w = self.owner[f_w]
        A[own_w, own_w] += self.diff[f_w]

        # --- 3. PRESSURE GRADIENT (The source of the crash) ---
        p_face = np.zeros(self.Nf)
        
        # Correctly use the specific indices for each face type
        p_face[f_int] = 0.5 * (self.P[own_i] + self.P[nei_i])
        p_face[f_in] = self.P[own_in] 
        p_face[self.outlet_faces] = self.outlet_pressure
        p_face[f_w] = self.P[own_w]

        # Vectorized force: b = -sum(P_f * Sf)
        # This remains the same, but now p_face is correctly sized
        np.add.at(b, self.owner, -p_face * self.Sf[:, axis])
        np.add.at(b, self.neighbor[f_int], p_face[f_int] * self.Sf[f_int, axis])
        
        # --- 4. UNDER-RELAXATION ---
        A_csr = A.tocsr()
        a_P = A_csr.diagonal().copy()
        alpha_u = 0.7
        
        A_diag = A_csr.diagonal()
        A_diag /= alpha_u
        A_csr.setdiag(A_diag)
        
        if hasattr(self, 'U_old'):
            b += (1 - alpha_u) / alpha_u * a_P * self.U[:, axis]
                                                        
        return A_csr, b, a_P
            
            
    def GET_VAR_STAR(self, A_u,b_u,A_v,b_v):
        
        u_star = spsolve(A_u, b_u)
        v_star = spsolve(A_v, b_v)
        
        return u_star,v_star
    
    def ASSEMBLE_PRESSURE_CORRECTION(self, a_P_u, a_P_v):
        A = lil_matrix((self.Nc, self.Nc))
        b = np.zeros(self.Nc)
        
        # --- 1. INTERNAL FACES ---
        f_int = self.internal_faces
        own_int = self.owner[f_int]
        nei_int = self.neighbor[f_int]
        
        d_f_int = self.rho * ( (self.Sf[f_int,0]**2)/a_P_u[own_int] + (self.Sf[f_int,1]**2)/a_P_v[own_int] )
        
        for i, f in enumerate(f_int):
            A[own_int[i], own_int[i]] += d_f_int[i]
            A[own_int[i], nei_int[i]] -= d_f_int[i]
            A[nei_int[i], nei_i[i]]   += d_f_int[i]
            A[nei_int[i], own_int[i]] -= d_f_int[i]
            
        # Mass imbalance (Internal)
        U_interp = (self.U[own_int] + self.U[nei_int]) / 2.0
        mass_flux_int = self.rho * np.sum(U_interp * self.Sf[f_int], axis=1)
        np.add.at(b, own_int, -mass_flux_int)
        np.add.at(b, nei_int, mass_flux_int)

        # --- 2. INLET FACES ---
        f_in = self.inlet_faces
        if len(f_in) > 0:
            own_in = self.owner[f_in]
            d_f_in = self.rho * ( (self.Sf[f_in,0]**2)/a_P_u[own_in] + (self.Sf[f_in,1]**2)/a_P_v[own_in] )
            for i, f in enumerate(f_in):
                A[own_in[i], own_in[i]] += d_f_in[i]
            
            mass_flux_in = self.rho * np.sum(self.inlet_velocity * self.Sf[f_in], axis=1)
            np.add.at(b, own_in, -mass_flux_in)

        # --- 3. OUTLET FACES (The "Pin") ---
        f_out = self.outlet_faces
        if len(f_out) > 0:
            own_out = self.owner[f_out]
            # USE UNIQUE NAMES HERE TO AVOID THE BROADCAST ERROR
            Sf_x_out = self.Sf[f_out, 0]
            Sf_y_out = self.Sf[f_out, 1]
            
            d_f_out = self.rho * ( (Sf_x_out**2)/a_P_u[own_out] + (Sf_y_out**2)/a_P_v[own_out] )
            
            for i, f in enumerate(f_out):
                A[own_out[i], own_out[i]] += d_f_out[i]
                
            mass_flux_out = self.rho * np.sum(self.U[own_out] * self.Sf[f_out], axis=1)
            np.add.at(b, own_out, -mass_flux_out)

        # --- 4. WALL FACES ---
        f_w = self.wall_faces
        if len(f_w) > 0:
            own_w = self.owner[f_w]
            d_f_w = self.rho * ( (self.Sf[f_w,0]**2)/a_P_u[own_w] + (self.Sf[f_w,1]**2)/a_P_v[own_w] )
            for i, f in enumerate(f_w):
                A[own_w[i], own_w[i]] += d_f_w[i]

        return A.tocsr(), b
    
    def GET_VAR_CORRECTED(self, A_p, b_p):

        p_prime = spsolve(A_p,b_p)
        
        return p_prime
    
    
    def CORRECT_PRESSURE_AND_VELOCITY(self, p_prime, a_P_u, a_P_v, u_star, v_star):
        """
        Apply pressure and velocity corrections (Fully Vectorized)
        """
        # Under-relaxation factors
        alpha_p = 0.3  # Pressure (conservative)
        
        # --- 1. UPDATE PRESSURE ---
        self.P += alpha_p * p_prime
        
        # --- 2. CORRECT VELOCITY ---
        # Initialize correction arrays
        u_correction = np.zeros(self.Nc)
        v_correction = np.zeros(self.Nc)
        correction_count = np.zeros(self.Nc) 
        
        # ==========================================
        # INTERNAL FACES
        # ==========================================
        f_int = self.internal_faces
        own_int = self.owner[f_int]
        nei_int = self.neighbor[f_int]
        
        # Gradients and Normals
        dp_prime_int = p_prime[nei_int] - p_prime[own_int]
        grad_p_prime_int = dp_prime_int / self.magDf[f_int]
        
        n_x_int = self.Sf[f_int, 0] / self.magSf[f_int]
        n_y_int = self.Sf[f_int, 1] / self.magSf[f_int]
        
        # Corrections for Owner cells
        d_u_own = self.magSf[f_int] / a_P_u[own_int]
        d_v_own = self.magSf[f_int] / a_P_v[own_int]
        
        u_corr_own = -d_u_own * grad_p_prime_int * n_x_int
        v_corr_own = -d_v_own * grad_p_prime_int * n_y_int
        
        # Corrections for Neighbor cells (opposite gradient push)
        d_u_nei = self.magSf[f_int] / a_P_u[nei_int]
        d_v_nei = self.magSf[f_int] / a_P_v[nei_int]
        
        u_corr_nei = d_u_nei * grad_p_prime_int * n_x_int
        v_corr_nei = d_v_nei * grad_p_prime_int * n_y_int
        
        # Accumulate using np.add.at (crucial for cells with multiple faces)
        np.add.at(u_correction, own_int, u_corr_own)
        np.add.at(v_correction, own_int, v_corr_own)
        np.add.at(correction_count, own_int, 1)
        
        np.add.at(u_correction, nei_int, u_corr_nei)
        np.add.at(v_correction, nei_int, v_corr_nei)
        np.add.at(correction_count, nei_int, 1)

        # ==========================================
        # BOUNDARY FACES (Inlets, Outlets, Walls)
        # ==========================================
        f_bnd = np.concatenate([self.inlet_faces, self.outlet_faces, self.wall_faces])
        own_bnd = self.owner[f_bnd]
        
        # For boundaries, assume p_prime_boundary = 0
        dp_prime_bnd = 0.0 - p_prime[own_bnd]
        grad_p_prime_bnd = dp_prime_bnd / self.magDf[f_bnd]
        
        n_x_bnd = self.Sf[f_bnd, 0] / self.magSf[f_bnd]
        n_y_bnd = self.Sf[f_bnd, 1] / self.magSf[f_bnd]
        
        d_u_bnd = self.magSf[f_bnd] / a_P_u[own_bnd]
        d_v_bnd = self.magSf[f_bnd] / a_P_v[own_bnd]
        
        u_corr_bnd = -d_u_bnd * grad_p_prime_bnd * n_x_bnd
        v_corr_bnd = -d_v_bnd * grad_p_prime_bnd * n_y_bnd
        
        # Accumulate boundary contributions
        np.add.at(u_correction, own_bnd, u_corr_bnd)
        np.add.at(v_correction, own_bnd, v_corr_bnd)
        np.add.at(correction_count, own_bnd, 1)

        # ==========================================
        # APPLY AVERAGED CORRECTIONS
        # ==========================================
        # Avoid division by zero for any disconnected cells
        correction_count[correction_count == 0] = 1 
        
        u_correction /= correction_count
        v_correction /= correction_count
        
        self.U[:, 0] = u_star + u_correction
        self.U[:, 1] = v_star + v_correction