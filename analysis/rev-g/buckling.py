"""Conservative-load linearized 3D buckling, K phi + lambda Kg phi = 0.

The geometric form is integral sigma_ij * v_k,i * u_k,j. All finite
prestress cells are retained. Fixed contact sets and small-strain isotropy
make this a computational screen, not nonlinear imperfection qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time
os.environ.setdefault('MKL_NUM_THREADS', '8')
import numpy as np
from scipy.sparse.linalg import eigsh, LinearOperator
from scipy.spatial import cKDTree
from skfem import MeshTet, Basis, ElementVector, ElementTetP1, ElementTetP2, BilinearForm, asm
from skfem.models.elasticity import linear_elasticity
from pypardiso import PyPardisoSolver

D = Path(__file__).resolve().parent


@BilinearForm
def negative_geometric_stiffness(u, v, w):
    return -np.einsum('ij...,ki...,kj...->...', w.stress, v.grad, u.grad)


def matrices(mesh, stress, E=1000., nu=.35, order=1):
    # On affine tetrahedra P2 displacement gradients are linear, so their
    # products integrate exactly with degree-2 quadrature (also for constant
    # cell prestress). Avoid allocating unnecessary higher-order quadrature.
    basis = Basis(mesh, ElementVector(ElementTetP1() if order == 1 else ElementTetP2()), intorder=2)
    mu = E/(2*(1+nu))
    lam = E*nu/((1+nu)*(1-2*nu))
    K = asm(linear_elasticity(lam, mu), basis).tocsr()
    B = asm(negative_geometric_stiffness, basis, stress=stress[:, :, :, None]).tocsr()
    return basis, K, B


def eigenpairs(K, B, fixed, count=4, tolerance=1e-7):
    free = np.setdiff1d(np.arange(K.shape[0]), np.unique(fixed))
    original_A, original_G = K[free][:, free], B[free][:, free]
    # Congruent diagonal scaling retains every element and eigenvalue while
    # improving conditioning around very small CAD-intersection tetrahedra.
    scale = 1/np.sqrt(original_A.diagonal())
    A = original_A.multiply(scale[:, None]).multiply(scale[None, :]).tocsr()
    G = original_G.multiply(scale[:, None]).multiply(scale[None, :]).tocsr()
    symmetry = float(np.max(abs((G-G.T).data))) if (G-G.T).nnz else 0.
    assert symmetry < 1e-9
    factor = PyPardisoSolver()
    print('buckling factor', A.shape[0], 'free DOFs', 'nnz', A.nnz, flush=True)
    factor.factorize(A)
    solves = [0]
    def inverse(x):
        solves[0] += 1
        result = factor.solve(A, x)
        for _ in range(2):
            result += factor.solve(A, x-A@result)
        return result
    M_inv = LinearOperator(A.shape, matvec=inverse, dtype=float)
    v0 = np.random.default_rng(20260910).normal(size=len(free))
    values, vectors = eigsh(G, M=A, Minv=M_inv, k=count, which='LA',
                            v0=v0, tol=tolerance, maxiter=500, ncv=max(24, 4*count+1))
    factor.free_memory(everything=True)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    vectors = scale[:, None]*vectors
    rows = []
    for value, vector in zip(values, vectors.T):
        residual = np.linalg.norm(original_G@vector-value*(original_A@vector))/(np.linalg.norm(original_G@vector)+np.linalg.norm(value*(original_A@vector)))
        print('buckling eigenpair', float(value), 'physical residual', float(residual), flush=True)
        assert residual < 1e-5, residual
        rows.append({'inverse_load_multiplier': float(value),
                     'critical_load_multiplier': float(1/value) if value > 0 else None,
                     'relative_eigen_residual': float(residual)})
    return rows, free, vectors, solves[0]


def validate():
    rows = []
    E, length, area, I = 1000., 20., 1., 1/12
    exact = np.pi**2*E*I/length**2
    for order, nx, ny in [(1, 80, 4), (1, 120, 6), (1, 160, 8), (2, 40, 2)]:
        mesh = MeshTet.init_tensor(np.linspace(0, length, nx+1),
                                  np.linspace(-.5, .5, ny+1), np.linspace(-.5, .5, ny+1))
        stress = np.zeros((3, 3, mesh.nelements))
        stress[0, 0] = -1.
        basis, K, B = matrices(mesh, stress, E=E, nu=0., order=order)
        xyz = basis.doflocs[:, ::3].T
        ends = np.flatnonzero(np.isclose(xyz[:, 0], 0) | np.isclose(xyz[:, 0], length))
        left = np.flatnonzero(np.isclose(xyz[:, 0], 0))
        anchor = left[np.argmin((xyz[left, 1:]**2).sum(axis=1))]
        fixed = np.concatenate([3*ends+1, 3*ends+2, [3*anchor]])
        modes, _, _, solves = eigenpairs(K, B, fixed, count=4)
        actual = modes[0]['critical_load_multiplier']*area
        error = abs(actual/exact-1)
        row = {'element_order': order, 'axial_divisions': nx, 'transverse_divisions': ny,
               'DOFs': K.shape[0], 'Euler_load_N': exact, 'FE_load_N': actual,
               'relative_difference': error, 'eigenpairs': modes, 'factor_solves': solves}
        rows.append(row)
        print('BEAM', json.dumps(row), flush=True)
    assert rows[1]['relative_difference'] < rows[0]['relative_difference']
    assert rows[2]['relative_difference'] < rows[1]['relative_difference']
    assert rows[2]['relative_difference'] < .05
    assert rows[3]['relative_difference'] < .02
    result = {'status': 'PASS', 'benchmark': '20 by 1 by 1 mm simply supported beam, uniform 1 MPa compression, E1000, nu0',
              'analytic_reference': 'Euler pi^2 E I / L^2',
              'note': 'Continuum shear compliance causes a small difference from the slender-beam expression.', 'cases': rows}
    (D/'buckling-validation.json').write_text(json.dumps(result, indent=2)+'\n')


def rack(field_path, output, order):
    assert json.loads((D/'buckling-validation.json').read_text())['status'] == 'PASS'
    started = time.perf_counter()
    with np.load(field_path, allow_pickle=False) as data:
        p, t, stress = data['p'], data['t'], data['stress']
        wall_nodes, active_wall = data['wall_nodes'], data['active_wall']
    mesh = MeshTet(p.T, t.T)
    basis, K, B = matrices(mesh, stress, order=order)
    xyz = basis.doflocs[:, ::3].T
    fixed = []
    for y in [164, 40]:
        r = np.hypot(xyz[:, 1]-y, xyz[:, 2]-12)
        head = np.flatnonzero((abs(xyz[:, 0]-3.6) < 1e-5) & (r > 2.75) & (r < 6.5))
        bore = np.flatnonzero((xyz[:, 0] < 3.61) & (abs(r-2.6) < .06))
        fixed.extend(3*head)
        fixed.extend(3*bore+1)
        fixed.extend(3*bore+2)
    wall = np.flatnonzero(abs(xyz[:, 0]) < 1e-5)
    nearest = cKDTree(p[wall_nodes]).query(xyz[wall])[1]
    active = wall[np.isin(wall_nodes[nearest], active_wall)]
    fixed.extend(3*active)
    modes, free, vectors, solves = eigenpairs(K, B, fixed, count=6)
    # Store nodal mode shapes for rendering; all modes use the complete domain.
    displacement = np.zeros((K.shape[0], len(modes)))
    displacement[free] = vectors
    for i in range(displacement.shape[1]):
        displacement[:, i] /= np.max(np.linalg.norm(displacement[:, i].reshape(-1, 3), axis=1))
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output.with_suffix('.npz'), p=p, t=t, mode_nodes=xyz,
                        modes=displacement.reshape(-1, 3, len(modes)))
    result = {'source_field': field_path.name, 'source_sha256': hashlib.sha256(field_path.read_bytes()).hexdigest(),
              'E_reference_MPa': 1000., 'element_order': order,
              'prestress_interpolation': 'Complete constant-strain tetrahedron field, no excluded cells',
              'modes': modes, 'lowest_positive_multiplier': min(r['critical_load_multiplier'] for r in modes if r['critical_load_multiplier'] is not None),
              'factor_solves': solves, 'seconds': time.perf_counter()-started,
              'limitations': 'Fixed converged wall contact set; conservative load direction; isotropic small-strain linear bifurcation. No geometric imperfections or nonlinear postbuckling.'}
    output.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--field', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--order', type=int, choices=[1, 2], default=1)
    args = parser.parse_args()
    if args.validate:
        validate()
    else:
        assert args.field and args.output
        rack(args.field, args.output, args.order)
