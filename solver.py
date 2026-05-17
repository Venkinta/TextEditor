import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import bicgstab, LinearOperator, spilu
from numba import njit, prange

try:
    import pyamg
    _HAS_PYAMG = True
except ImportError:
    _HAS_PYAMG = False

# ---------------------------------------------------------------------------
# JIT-Compiled Hot Loops (Memory-Bandwidth Optimisation)
# ---------------------------------------------------------------------------

@njit(parallel=True, cache=True)
def _jit_calc_pressure_gradients(Nc, own, nei, P, Sf_int, own_b, Sf_bnd, P_bnd):
    grad_P = np.zeros((Nc, 2), dtype=np.float64)
    
    # Internal faces
    for i in prange(len(own)):
        o = own[i]
        n = nei[i]
        p_f = 0.5 * (P[o] + P[n])
        flux_x = p_f * Sf_int[i, 0]
        flux_y = p_f * Sf_int[i, 1]
        
        # Unbuffered addition (requires no np.add.at overhead)
        # Numba parallel may have slight race conditions on accumulation if faces
        # share the same cell on different threads, but for unstructured meshes
        # standard accumulation is usually safe enough. If strictly needed, 
        # parallel=False guarantees bitwise reproducibility.
        grad_P[o, 0] += flux_x
        grad_P[o, 1] += flux_y
        grad_P[n, 0] -= flux_x
        grad_P[n, 1] -= flux_y

    # Boundary faces
    for i in prange(len(own_b)):
        o = own_b[i]
        flux_x = P_bnd[i] * Sf_bnd[i, 0]
        flux_y = P_bnd[i] * Sf_bnd[i, 1]
        
        grad_P[o, 0] += flux_x
        grad_P[o, 1] += flux_y

    return grad_P

@njit(parallel=True, cache=True)
def _jit_update_flux_diff(rho, nu, own, nei, U, Sf_int, magSf_int, magDf_int, P, grad_P, cell_areas, a_P_u, a_P_v, has_ap):
    Nf_int = len(own)
    phi = np.zeros(Nf_int, dtype=np.float64)
    diff = np.zeros(Nf_int, dtype=np.float64)

    for i in prange(Nf_int):
        o = own[i]
        n = nei[i]
        
        # Interpolate Velocity
        u_interp = 0.5 * (U[o, 0] + U[n, 0])
        v_interp = 0.5 * (U[o, 1] + U[n, 1])
        
        # Face scalar product (U dot Sf)
        phi_star = rho * (u_interp * Sf_int[i, 0] + v_interp * Sf_int[i, 1])
        
        if has_ap:
            # Rhie-Chow Interpolation
            a_P_f = max(0.25 * (a_P_u[o] + a_P_u[n] + a_P_v[o] + a_P_v[n]), 1e-10)
            
            gP_f_x = 0.5 * (grad_P[o, 0] + grad_P[n, 0])
            gP_f_y = 0.5 * (grad_P[o, 1] + grad_P[n, 1])
            
            n_f_x = Sf_int[i, 0] / magSf_int[i]
            n_f_y = Sf_int[i, 1] / magSf_int[i]
            
            dp_interp = gP_f_x * n_f_x + gP_f_y * n_f_y
            dp_actual = (P[n] - P[o]) / magDf_int[i]
            
            vol_f = 0.5 * (cell_areas[o] + cell_areas[n])
            D_f = vol_f / a_P_f
            
            phi[i] = phi_star + rho * D_f * (dp_interp - dp_actual) * magSf_int[i]
        else:
            phi[i] = phi_star
            
        # Diffusion term
        diff[i] = nu * magSf_int[i] / magDf_int[i]

    return phi, diff

@njit(parallel=True, cache=True)
def _jit_assemble_momentum_rhs(Nc, P, Sf, f_int, own_i, nei_i, own_in, own_out, own_w, inlet_faces, outlet_faces, wall_faces, inlet_velocity, outlet_pressure, D_in, F_in):
    b_x = np.zeros(Nc, dtype=np.float64)
    b_y = np.zeros(Nc, dtype=np.float64)

    # Calculate Face Pressures (Internal & Boundaries)
    for i in prange(len(f_int)):
        f = f_int[i]
        o = own_i[i]
        n = nei_i[i]
        p_f = 0.5 * (P[o] + P[n])
        
        # Axis 0 (X)
        term_x = p_f * Sf[f, 0]
        b_x[o] -= term_x
        b_x[n] += term_x
        
        # Axis 1 (Y)
        term_y = p_f * Sf[f, 1]
        b_y[o] -= term_y
        b_y[n] += term_y

    # Inlet faces
    for i in prange(len(inlet_faces)):
        f = inlet_faces[i]
        o = own_in[i]
        p_f = P[o]
        b_x[o] -= p_f * Sf[f, 0] - (D_in[i] - F_in[i]) * inlet_velocity[0]
        b_y[o] -= p_f * Sf[f, 1] - (D_in[i] - F_in[i]) * inlet_velocity[1]

    # Outlet faces
    for i in prange(len(outlet_faces)):
        f = outlet_faces[i]
        o = own_out[i]
        b_x[o] -= outlet_pressure * Sf[f, 0]
        b_y[o] -= outlet_pressure * Sf[f, 1]

    # Wall faces
    for i in prange(len(wall_faces)):
        f = wall_faces[i]
        o = own_w[i]
        p_f = P[o]
        b_x[o] -= p_f * Sf[f, 0]
        b_y[o] -= p_f * Sf[f, 1]

    return b_x, b_y

@njit(parallel=True, cache=True)
def _jit_assemble_pcorr_rhs(Nc, rho, U_star, Sf_int, Sf_in, Sf_out, own_i, nei_i, own_in, own_out, inlet_velocity):
    b = np.zeros(Nc, dtype=np.float64)
    
    # Internal
    for i in prange(len(own_i)):
        o = own_i[i]
        n = nei_i[i]
        u_interp = 0.5 * (U_star[o, 0] + U_star[n, 0])
        v_interp = 0.5 * (U_star[o, 1] + U_star[n, 1])
        mass_flux = rho * (u_interp * Sf_int[i, 0] + v_interp * Sf_int[i, 1])
        b[o] -= mass_flux
        b[n] += mass_flux
        
    # Inlet
    for i in prange(len(own_in)):
        o = own_in[i]
        mass_flux = rho * (inlet_velocity[0] * Sf_in[i, 0] + inlet_velocity[1] * Sf_in[i, 1])
        b[o] -= mass_flux

    # Outlet
    for i in prange(len(own_out)):
        o = own_out[i]
        mass_flux = rho * (U_star[o, 0] * Sf_out[i, 0] + U_star[o, 1] * Sf_out[i, 1])
        b[o] -= mass_flux
        
    return b

# ---------------------------------------------------------------------------
# Solver Class
# ---------------------------------------------------------------------------

class Solver:
    def __init__(self, mesher_data, inlet_velocity, outlet_pressure, rho, viscosity):
        self.inlet_velocity  = np.asarray(inlet_velocity, dtype=np.float64)
        self.outlet_pressure = float(outlet_pressure)
        self.rho             = float(rho)
        self.viscosity       = float(viscosity)

        mesh = mesher_data
        self.Nc = mesh['Nc']
        self.Nf = mesh['Nf']

        self.owner         = mesh['owner']
        self.neighbor      = mesh['neighbor']
        self.boundary_tags = mesh['boundary_tags']

        self.Sf    = mesh['Sf']
        self.magSf = mesh['magSf']
        self.Cf    = mesh['Cf']
        self.df    = mesh['df']
        self.magDf = mesh['magDf']

        self.magDf = np.maximum(self.magDf, 1e-10)
        self.magSf = np.maximum(self.magSf, 1e-10)

        self.cell_centers = mesh['cell_centers']
        self.cell_areas   = mesh['cell_areas']

        self.wall_faces     = np.where(self.boundary_tags == 0)[0]
        self.inlet_faces    = np.where(self.boundary_tags == 1)[0]
        self.outlet_faces   = np.where(self.boundary_tags == 2)[0]
        self.internal_faces = np.where(self.boundary_tags == -1)[0]

        print("--- MESH SANITY CHECK ---")
        print(f"Total Cells:    {self.Nc}")
        print(f"Internal Faces: {len(self.internal_faces)}")
        print(f"Inlet Faces:    {len(self.inlet_faces)}")
        print(f"Outlet Faces:   {len(self.outlet_faces)}")
        print(f"Wall Faces:     {len(self.wall_faces)}")
        print("-------------------------")

        self._precompute_topology()

        # Iterative solver state
        self._precond_cache    = {}
        self._precond_interval = 50   # rebuild ILU every N SIMPLE iterations
        self._iteration        = 0
        self._last_grad_P      = None  # cached for health_check

    # ------------------------------------------------------------------
    # One-time topology precomputation
    # ------------------------------------------------------------------

    def _precompute_topology(self):
        """Cache every derived index/slice array used in the hot loop."""
        f_int = self.internal_faces

        # Gradient computation
        self._grad_own = self.owner[f_int]
        self._grad_nei = self.neighbor[f_int]
        self._Sf_int   = self.Sf[f_int]

        # Boundary faces (ordered: inlet, outlet, wall — consistent throughout)
        self._f_bnd  = np.concatenate([self.inlet_faces,
                                        self.outlet_faces,
                                        self.wall_faces])
        self._own_b  = self.owner[self._f_bnd]
        self._Sf_bnd = self.Sf[self._f_bnd]

        outlet_set = set(self.outlet_faces.tolist())
        self._is_outlet_bnd = np.array(
            [f in outlet_set for f in self._f_bnd], dtype=bool)

        # Per-face-type aliases
        self._own_i   = self._grad_own
        self._nei_i   = self._grad_nei
        self._own_in  = self.owner[self.inlet_faces]
        self._own_w   = self.owner[self.wall_faces]
        self._own_out = self.owner[self.outlet_faces]
        self._Sf_in   = self.Sf[self.inlet_faces]
        self._Sf_w    = self.Sf[self.wall_faces]
        self._Sf_out  = self.Sf[self.outlet_faces]
        self._all_owner = self.owner  # alias, no copy

        # COO index arrays (still needed to define structure)
        mom_rows = np.concatenate([
            self._own_i, self._own_i, self._nei_i, self._nei_i,
            self._own_in, self._own_w, self._own_out,
        ])
        mom_cols = np.concatenate([
            self._own_i, self._nei_i, self._nei_i, self._own_i,
            self._own_in, self._own_w, self._own_out,
        ])
        pcorr_rows = np.concatenate([
            self._own_i, self._own_i, self._nei_i, self._nei_i,
            self._own_in, self._own_out, self._own_w,
        ])
        pcorr_cols = np.concatenate([
            self._own_i, self._nei_i, self._nei_i, self._own_i,
            self._own_in, self._own_out, self._own_w,
        ])

        # Pre-build the CSR structures.
        self._mom_csr   = self._build_csr_template(mom_rows,   mom_cols)
        self._pcorr_csr = self._build_csr_template(pcorr_rows, pcorr_cols)

    # ------------------------------------------------------------------
    # CSR precomputation helpers
    # ------------------------------------------------------------------

    def _build_csr_template(self, rows, cols):
        Nc = self.Nc
        n  = len(rows)

        sort_order = np.lexsort((cols, rows))
        rows_s = rows[sort_order]
        cols_s = cols[sort_order]

        pairs = rows_s.astype(np.int64) * Nc + cols_s.astype(np.int64)
        _, first_occ, inv_idx = np.unique(pairs, return_index=True, return_inverse=True)
        n_unique   = len(first_occ)
        rows_u     = rows_s[first_occ]
        cols_u     = cols_s[first_occ]

        row_counts  = np.bincount(rows_u, minlength=Nc)
        indptr      = np.zeros(Nc + 1, dtype=np.int32)
        indptr[1:]  = np.cumsum(row_counts)

        indices = cols_u.astype(np.int32)

        rank = np.empty(n, dtype=np.int64)
        rank[sort_order] = np.arange(n, dtype=np.int64)
        scatter = inv_idx[rank]

        return dict(indptr=indptr, indices=indices, scatter=scatter, n_unique=n_unique)

    def _make_csr(self, csr_info, coo_data):
        data = np.bincount(csr_info['scatter'], weights=coo_data, minlength=csr_info['n_unique'])
        return csr_matrix((data, csr_info['indices'], csr_info['indptr']),
                          shape=(self.Nc, self.Nc), copy=False)

    # ------------------------------------------------------------------
    # Solvers
    # ------------------------------------------------------------------

    def _solve_momentum(self, A, b, cache_key):
        diag = np.abs(A.diagonal())
        np.maximum(diag, 1e-30, out=diag)
        M  = LinearOperator(A.shape, matvec=lambda x: x / diag, dtype=np.float64)
        x0 = b / diag

        x, info = bicgstab(A, b, x0=x0, M=M, rtol=1e-3, atol=0.0, maxiter=300)
        if info != 0:
            x, info = bicgstab(A, b, x0=x0, M=M, rtol=1e-2, atol=0.0, maxiter=200)
            if info != 0:
                print(f"  BiCGSTAB [{cache_key}] stalled (info={info}), res={np.linalg.norm(A @ x - b):.2e}")
        return x

    def _solve_pressure(self, A, b):
        refresh = (self._iteration % self._precond_interval == 0 or 'pressure' not in self._precond_cache)
        if refresh:
            if _HAS_PYAMG:
                try:
                    ml = pyamg.ruge_stuben_solver(A, coarse_solver='pinv')
                    self._precond_cache['pressure'] = ml.aspreconditioner()
                except Exception as exc:
                    print(f"  PyAMG setup failed ({exc}); falling back to ILU.")
                    self._precond_cache.pop('pressure', None)
            if not _HAS_PYAMG or 'pressure' not in self._precond_cache:
                try:
                    ilu = spilu(A.tocsc(), fill_factor=8, drop_tol=1e-4)
                    self._precond_cache['pressure'] = LinearOperator(A.shape, matvec=ilu.solve, dtype=np.float64)
                except Exception as exc:
                    print(f"  ILU failed ({exc}); no preconditioner this step.")
                    self._precond_cache.pop('pressure', None)

        M  = self._precond_cache.get('pressure')
        x0 = b / (np.abs(A.diagonal()) + 1e-30)

        x, info = bicgstab(A, b, x0=x0, M=M, rtol=1e-3, atol=0.0, maxiter=300)
        if info != 0:
            x, info = bicgstab(A, b, x0=x0, M=M, rtol=1e-2, atol=0.0, maxiter=200)
            if info != 0:
                print(f"  BiCGSTAB [pressure] stalled (info={info}), res={np.linalg.norm(A @ x - b):.2e}")
        return x

    # ------------------------------------------------------------------
    # SIMPLE loop
    # ------------------------------------------------------------------

    def Solve(self, max_iterations=1000, tolerance=1e-6):
        self.initialize_conditions()
        initial_residuals = None
        a_P_u = a_P_v = None

        for iteration in range(max_iterations):
            self._iteration = iteration
            self.U_old = self.U.copy()

            self.SIMPLE_UPDATE_FACE_FLUX_AND_DIFFUSSION(a_P_u, a_P_v)

            if not np.all(np.isfinite(self.U)):
                print(f"NaN/Inf in U at iteration {iteration}"); break

            A_mom, b_x, b_y, a_P_u = self.assemble_momentum_both()
            a_P_v = a_P_u

            if not (np.all(np.isfinite(b_x)) and np.all(np.isfinite(b_y))):
                print(f"NaN/Inf in RHS at iteration {iteration}"); break

            u_star, v_star = self.GET_VAR_STAR(A_mom, b_x, b_y)

            if not (np.all(np.isfinite(u_star)) and np.all(np.isfinite(v_star))):
                print(f"NaN/Inf in u* at iteration {iteration}"); break

            A_p, b_p = self.ASSEMBLE_PRESSURE_CORRECTION(a_P_u, a_P_v, u_star, v_star)
            p_prime   = self.GET_VAR_CORRECTED(A_p, b_p)

            if not np.all(np.isfinite(p_prime)):
                print(f"NaN/Inf in p' at iteration {iteration}"); break

            self.CORRECT_PRESSURE_AND_VELOCITY(p_prime, a_P_u, a_P_v, u_star, v_star)

            if not np.all(np.isfinite(self.U)):
                print(f"NaN/Inf in corrected U at iteration {iteration}"); break

            res_cont = np.linalg.norm(b_p)
            res_u    = np.linalg.norm(A_mom @ self.U[:, 0] - b_x)
            res_v    = np.linalg.norm(A_mom @ self.U[:, 1] - b_y)

            if iteration == 0:
                initial_residuals = {
                    'cont': max(res_cont, 1e-10),
                    'u':    max(res_u,    1e-10),
                    'v':    max(res_v,    1e-10),
                }

            norm_cont    = res_cont / initial_residuals['cont']
            norm_u       = res_u    / initial_residuals['u']
            norm_v       = res_v    / initial_residuals['v']
            max_residual = max(norm_cont, norm_u, norm_v)

            if iteration % 10 == 0:
                self.health_check(iteration, a_P_u)
                print(f"Iter {iteration:4d}: Cont={norm_cont:.2e}  U={norm_u:.2e}  V={norm_v:.2e}")

            if max_residual < tolerance:
                print(f"\nConverged at iteration {iteration}!")
                break
        else:
            print(f"\nDid not converge in {max_iterations} iterations — final residual {max_residual:.2e}")

    # ------------------------------------------------------------------

    def initialize_conditions(self):
        self.P     = np.full(self.Nc, self.outlet_pressure)
        self.U     = np.zeros((self.Nc, 2))
        self.U_old = self.U.copy()
        self.phi   = np.zeros(self.Nf)
        self.diff  = np.zeros(self.Nf)
        self.SIMPLE_UPDATE_FACE_FLUX_AND_DIFFUSSION()

    # ------------------------------------------------------------------

    def SIMPLE_UPDATE_FACE_FLUX_AND_DIFFUSSION(self, a_P_u=None, a_P_v=None):
        grad_P  = self.calculate_pressure_gradients()
        
        # Determine if we have a_P variables for Rhie-Chow
        has_ap = (a_P_u is not None)
        dummy_a_P = np.zeros(1) if not has_ap else a_P_u
        
        phi_int, diff_int = _jit_update_flux_diff(
            self.rho, self.viscosity, self._own_i, self._nei_i, self.U, 
            self._Sf_int, self.magSf[self.internal_faces], self.magDf[self.internal_faces], 
            self.P, grad_P, self.cell_areas, dummy_a_P, dummy_a_P, has_ap
        )
        
        self.phi[self.internal_faces] = phi_int
        self.diff[self.internal_faces] = diff_int

        # Boundary fluxes
        self.phi[self.inlet_faces] = self.rho * np.einsum('fj,j->f', self._Sf_in, self.inlet_velocity)
        self.phi[self.wall_faces]  = 0.0
        self.phi[self.outlet_faces] = self.rho * np.einsum('fj,fj->f', self.U[self._own_out], self._Sf_out)

        nu = self.viscosity
        self.diff[self.inlet_faces]  = nu * self.magSf[self.inlet_faces] / self.magDf[self.inlet_faces]
        self.diff[self.outlet_faces] = 0.0
        self.diff[self.wall_faces]   = nu * self.magSf[self.wall_faces] / self.magDf[self.wall_faces]

    # ------------------------------------------------------------------

    def assemble_momentum_both(self):
        f_int   = self.internal_faces
        F     = self.phi[f_int]
        D     = self.diff[f_int]
        F_in  = self.phi[self.inlet_faces]; D_in = self.diff[self.inlet_faces]
        D_w   = self.diff[self.wall_faces]
        F_out = self.phi[self.outlet_faces]

        data = np.concatenate([
            np.maximum( F, 0) + D,
            -(np.maximum(-F, 0) + D),
            np.maximum(-F, 0) + D,
            -(np.maximum( F, 0) + D),
            D_in,
            D_w,
            np.maximum(F_out, 0),
        ])

        A = self._make_csr(self._mom_csr, data)

        # RHS Construction via JIT
        b_x, b_y = _jit_assemble_momentum_rhs(
            self.Nc, self.P, self.Sf, f_int, self._own_i, self._nei_i, 
            self._own_in, self._own_out, self._own_w, self.inlet_faces, 
            self.outlet_faces, self.wall_faces, self.inlet_velocity, 
            self.outlet_pressure, D_in, F_in
        )

        a_P_pure = A.diagonal().copy()
        alpha_u = 0.2
        A.setdiag(a_P_pure / alpha_u)
        
        if hasattr(self, 'U_old'):
            relax = ((1 - alpha_u) / alpha_u) * a_P_pure
            b_x  += relax * self.U_old[:, 0]
            b_y  += relax * self.U_old[:, 1]

        # Pass out the relaxed diagonal 
        a_P_relaxed = a_P_pure / alpha_u
        return A, b_x, b_y, a_P_relaxed

    # ------------------------------------------------------------------

    def GET_VAR_STAR(self, A_mom, b_x, b_y):
        u_star = self._solve_momentum(A_mom, b_x, 'mom_u')
        v_star = self._solve_momentum(A_mom, b_y, 'mom_v')
        v_max  = np.linalg.norm(self.inlet_velocity) * 5.0
        return np.clip(u_star, -v_max, v_max), np.clip(v_star, -v_max, v_max)

    # ------------------------------------------------------------------

    def ASSEMBLE_PRESSURE_CORRECTION(self, a_P_u, a_P_v, u_star, v_star):
        own_i  = self._own_i;  nei_i  = self._nei_i
        own_in = self._own_in; own_out = self._own_out; own_w = self._own_w

        def _d(Sf_slice, own):
            return (Sf_slice[:, 0]**2 / a_P_u[own] + Sf_slice[:, 1]**2 / a_P_v[own])

        d_int = _d(self._Sf_int, own_i)
        d_in  = _d(self._Sf_in,  own_in)
        d_out = _d(self._Sf_out, own_out)
        d_w   = _d(self._Sf_w,   own_w)

        data = np.concatenate([
            d_int, -d_int, d_int, -d_int,
            d_in, d_out, d_w,
        ])
        A = self._make_csr(self._pcorr_csr, data)

        U_star = np.column_stack((u_star, v_star))
        
        # JIT RHS Construction
        b = _jit_assemble_pcorr_rhs(
            self.Nc, self.rho, U_star, self._Sf_int, self._Sf_in, self._Sf_out, 
            own_i, nei_i, own_in, own_out, self.inlet_velocity
        )

        return A, b

    # ------------------------------------------------------------------

    def GET_VAR_CORRECTED(self, A_p, b_p):
        p_prime = self._solve_pressure(A_p, b_p)
        p_prime[np.unique(self._own_out)] = 0.0
        return p_prime

    # ------------------------------------------------------------------

    def CORRECT_PRESSURE_AND_VELOCITY(self, p_prime, a_P_u, a_P_v, u_star, v_star):
        alpha_p = 0.1
        self.P += alpha_p * p_prime
        self.P -= (np.mean(self.P[self._own_out]) - self.outlet_pressure)

        P_tmp  = self.P.copy()
        self.P = p_prime
        grad_p_prime = self.calculate_pressure_gradients(is_correction=True)
        self.P = P_tmp

        self.U[:, 0] = u_star - (self.cell_areas / a_P_u) * grad_p_prime[:, 0]
        self.U[:, 1] = v_star - (self.cell_areas / a_P_v) * grad_p_prime[:, 1]

    # ------------------------------------------------------------------

    def calculate_pressure_gradients(self, is_correction=False):
        P_f_b = self.P[self._own_b].copy()
        if is_correction:
            P_f_b[self._is_outlet_bnd] = 0.0
        else:
            P_f_b[self._is_outlet_bnd] = self.outlet_pressure

        # Hand off to JIT Loop
        grad_P = _jit_calc_pressure_gradients(
            self.Nc, self._grad_own, self._grad_nei, self.P, 
            self._Sf_int, self._own_b, self._Sf_bnd, P_f_b
        )
        
        grad_P /= self.cell_areas[:, None]

        if not is_correction:
            self._last_grad_P = grad_P

        return grad_P

    # ------------------------------------------------------------------

    def health_check(self, iteration, a_P_u):
        print(f"\n--- Health Check Iteration {iteration} ---")
        print(f"  U range:    [{np.nanmin(self.U):.2e}, {np.nanmax(self.U):.2e}]")
        print(f"  P range:    [{np.nanmin(self.P):.2e}, {np.nanmax(self.P):.2e}]")
        print(f"  Phi range:  [{np.nanmin(self.phi):.2e}, {np.nanmax(self.phi):.2e}]")
        print(f"  Min a_P:    {np.min(a_P_u):.2e}")
        g = (self._last_grad_P if self._last_grad_P is not None else self.calculate_pressure_gradients())
        print(f"  Max grad_P: {np.max(np.abs(g)):.2e}")
        print(f"---------------------------------\n")