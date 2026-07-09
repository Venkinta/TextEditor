import numpy as np


def save_mesh_for_solver(mesh_data, filepath):
    """Dumps the solver dictionary to a compressed .npz file.

    `mesh_data` is the dict produced by Mesher.solver_data_pipeline() (which
    now also carries cell-vertex geometry for the Visualizer).  The Solver
    only reads the fields it needs; the extra arrays are ignored on load.
    """
    np.savez_compressed(filepath, **mesh_data)
    print(f"[IO] Mesh successfully exported to {filepath}")


def load_mesh_for_solver(filepath):
    """Loads a saved mesh file directly into a clean Python dictionary for the solver."""
    with np.load(filepath) as loaded:
        # Reconstruct the dictionary
        data = {key: loaded[key] for key in loaded.files}

    # Note: np.savez converts Python scalars into 0-dimensional arrays.
    # Let's cast Nc and Nf back to normal Python integers for solver sanity.
    data['Nc'] = int(data['Nc'])
    data['Nf'] = int(data['Nf'])

    print(f"[IO] Mesh successfully loaded from {filepath} ({data['Nc']} cells, {data['Nf']} faces)")
    return data