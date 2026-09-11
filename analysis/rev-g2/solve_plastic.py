"""3D mechanics on the slicer-derived material domain, N/mm/MPa.

G interface positions and load split are retained for the regression check.
The input mesh contains no sacrificial thick bridges. This is an isotropic
printed-material screen, with rigid fasteners and unilateral flat-wall contact.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

os.environ.setdefault('MKL_NUM_THREADS', '8')
import numpy as np
from scipy.sparse.linalg import splu
from skfem import MeshTet, Basis, ElementTetP1, ElementVector, asm
from skfem.models.elasticity import linear_elasticity


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interface_loads(total):
    span = np.hypot(100, 12)
    rise = np.sqrt((90+12.4)**2-span**2/4)
    cx, cy = 140-12*rise/span, 6+100*rise/span
    a, b = cx-90, 190-cx
    den = a*(cy-12)+b*cy
    horizontal = total*a*b/den
    rear = total*b*cy/den
    front = total*a*(cy-12)/den
    return {'rear_seat': np.array([-horizontal, -rear, 0.]),
            'front_seat': np.array([horizontal, -front, 0.])}


def solve(args):
    start = time.perf_counter()
    data = np.load(args.mesh)
    p, t = data['p'], data['t']
    assert np.isfinite(p).all() and len(np.unique(t)) == len(p)
    n = len(p)
    mesh = MeshTet(p.T, t.T)
    basis = Basis(mesh, ElementVector(ElementTetP1()))
    mu = args.E/(2*(1+args.nu))
    lam = args.E*args.nu/((1+args.nu)*(1-2*args.nu))
    tri = mesh.facets[:, mesh.boundary_facets()].T
    v = p[tri]
    cent = v.mean(axis=1)
    normal = np.cross(v[:, 1]-v[:, 0], v[:, 2]-v[:, 0])
    length = np.linalg.norm(normal, axis=1)
    assert np.all(length > 0)
    normal /= length[:, None]
    area = length/2
    f = np.zeros(3*n)
    patches = {}
    for x, y, label in [(90., 0., 'rear_seat'), (190., 12., 'front_seat')]:
        force = interface_loads(args.load_N)[label]
        radial = np.hypot(cent[:, 0]-x, cent[:, 1]-y)
        theta = np.arctan2(cent[:, 1]-y, cent[:, 0]-x)
        target = np.arctan2(force[1], force[0])
        offset = np.arctan2(np.sin(theta-target), np.cos(theta-target))
        mask = (abs(radial-13) < .12+args.surface_tolerance_mm) & (abs(offset) < np.deg2rad(25))
        # Broad-side skin faces near a seat are not the rod bearing interface.
        mask &= abs(normal[:, 2]) < .5
        ids, weights = tri[mask], area[mask]
        assert len(ids), label
        for j in range(3):
            for k in range(3):
                np.add.at(f, 3*ids[:, j]+k, weights/weights.sum()/3*force[k])
        patches[label] = {'area_mm2': float(weights.sum()), 'facets': int(mask.sum()),
                          'force_N': force.tolist(), 'nodes': np.unique(ids)}
    fixed_base = []
    heads = {}
    interfaces = {}
    tol = args.surface_tolerance_mm
    for y in [164., 40.]:
        rface = np.hypot(cent[:, 1]-y, cent[:, 2]-12)
        head_mask = (abs(cent[:, 0]-3.6) < tol) & (rface > 2.75) & (rface < 6.5) & (abs(normal[:, 0]) > .9)
        head = np.unique(tri[head_mask])
        head_radius = np.hypot(p[head, 1]-y, p[head, 2]-12)
        head = head[(head_radius > 2.75) & (head_radius < 6.5) & (abs(p[head, 0]-3.6) < tol)]
        bore_mask = (cent[:, 0] < 3.6+tol) & (abs(rface-2.6) < .08+tol) & (abs(normal[:, 0]) < .5)
        bore = np.unique(tri[bore_mask])
        assert len(head) and len(bore), ('Missing fastener interface', y)
        fixed_base.extend(3*head)
        fixed_base.extend(3*bore+1)
        fixed_base.extend(3*bore+2)
        heads[str(int(y))] = head
        import shapely
        from shapely.geometry import Point
        washer_ring = Point(y, 12).buffer(6.5, quad_segs=64).difference(Point(y, 12).buffer(2.75, quad_segs=64))
        projected_faces = shapely.polygons(v[head_mask][:, :, 1:])
        clipped_area = shapely.area(shapely.intersection(projected_faces, washer_ring))/abs(normal[head_mask, 0])
        interfaces[str(int(y))] = {'washer_nodes': len(head), 'bore_nodes': len(bore),
                                   'washer_clipped_face_area_mm2': float(clipped_area.sum()),
                                   'bore_face_area_mm2': float(area[bore_mask].sum())}
    wall_mask = (cent[:, 0] < tol) & (abs(normal[:, 0]) > .9)
    wall = np.unique(tri[wall_mask])
    assert len(wall)
    base = np.unique(fixed_base).astype(int)
    # The flat wall touches the rear-most reconstructed wall point. Preserve
    # geometric roughness as initial gap instead of clamping a tolerance strip.
    wall_plane_x = float(p[wall, 0].min())
    gap0 = p[wall, 0]-wall_plane_x
    assert gap0.min() >= -1e-10
    if args.flat_wall_reference:
        gap0[:] = 0.
    report = {'mesh_sha256': digest(args.mesh), 'nodes': n, 'tetrahedra': len(t),
              'E_reference_MPa': args.E, 'nu': args.nu, 'load_N': args.load_N,
              'load_model': 'G 180 mm spool statics, distributed over a 50 degree seat-bearing arc.',
              'fastener_model': 'Rigid washer axial restraint and rigid shank lateral bearing; hardware and substrate capacity are separate.',
              'wall_model': 'Frictionless unilateral plane at rear-most reconstructed wall point; initial geometric gaps retained.' if not args.flat_wall_reference else 'Ideal flush wall comparison; initial gaps suppressed explicitly.',
              'wall_plane_x_mm': wall_plane_x,
              'maximum_initial_wall_gap_mm': float(gap0.max()),
              'surface_classification_tolerance_mm': tol, 'fastener_interfaces': interfaces,
              'sacrificial_bridge_structural_credit': 0,
              'element': 'Constant-strain tetrahedron; all finite cells retained.',
              'material_basis': 'E=1 GPa effective-modulus planning screen. Isotropic surrogate; no lifetime strength claim.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_name(args.output.name+'-interfaces.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if args.interfaces_only:
        print(json.dumps(report, indent=2), flush=True)
        return
    print('assemble', n, len(t), flush=True)
    K = asm(linear_elasticity(lam, mu), basis).tocsr()
    diagonal = K.diagonal()
    active = wall[gap0 < 1e-9]
    u = np.zeros(3*n)
    iterations = []
    converged = False
    for step in range(40):
        fixed = np.union1d(base, 3*active)
        free = np.setdiff1d(np.arange(3*n), fixed)
        u[:] = 0.
        active_index = np.searchsorted(wall, active)
        u[3*active] = -gap0[active_index]
        A = K[free][:, free]
        rhs = f[free]-K[free][:, fixed]@u[fixed]
        if args.solver == 'pardiso':
            from pypardiso import PyPardisoSolver
            factor = PyPardisoSolver()
            factor.factorize(A)
            sol = factor.solve(A, rhs)
            for k in range(5):
                sol += factor.solve(A, rhs-A@sol)
            factor.free_memory(everything=True)
        else:
            factor = splu(A.tocsc(), permc_spec='MMD_AT_PLUS_A', options={'Equil': True})
            sol = factor.solve(rhs)
            for k in range(3):
                sol += factor.solve(rhs-A@sol)
        u[free] = sol
        reaction = K@u-f
        gaps = u[3*wall]+gap0
        new = wall[(reaction[3*wall]-diagonal[3*wall]*gaps) > 1e-7]
        iterations.append({'step': step, 'active_wall_nodes': len(active), 'next_active_wall_nodes': len(new),
                           'minimum_gap_mm': float(gaps.min())})
        print('contact', step, len(active), '->', len(new), 'min gap', gaps.min(), flush=True)
        if np.array_equal(new, active):
            converged = True
            break
        active = new
    assert converged, 'Contact active set did not converge'
    residual = np.linalg.norm(reaction[free])/max(np.linalg.norm(f[free]), 1e-30)
    applied = f.reshape(-1, 3)
    reacted = reaction.reshape(-1, 3)
    force_error = np.linalg.norm(applied.sum(axis=0)+reacted.sum(axis=0))/max(1., np.linalg.norm(applied.sum(axis=0)))
    amoment, rmoment = np.cross(p, applied).sum(axis=0), np.cross(p, reacted).sum(axis=0)
    moment_error = np.linalg.norm(amoment+rmoment)/max(1., np.linalg.norm(amoment))
    assert max(residual, force_error, moment_error) < 1e-6, (residual, force_error, moment_error)
    assert gaps.min() > -1e-7 and (not len(active) or reaction[3*active].min() > -1e-7)
    U = u.reshape(-1, 3)
    gradient = basis.interpolate(u).grad.mean(axis=-1)
    strain = (gradient+gradient.transpose(1, 0, 2))/2
    stress = 2*mu*strain+lam*np.einsum('iie->e', strain)[None, None, :]*np.eye(3)[:, :, None]
    principal = np.linalg.eigvalsh(stress.transpose(2, 0, 1))
    deviator = stress-np.einsum('iie->e', stress)[None, None, :]*np.eye(3)[:, :, None]/3
    vm = np.sqrt(1.5*np.einsum('ije,ije->e', deviator, deviator))
    volume = basis.dx.sum(axis=1)
    assert np.isfinite(stress).all() and np.isfinite(U).all() and np.all(volume > 0)
    tc = p[t].mean(axis=1)
    maximum = int(np.argmax(principal[:, 2]))
    report.update({'contact_converged': converged, 'contact_iterations': iterations,
                   'relative_free_residual': float(residual), 'relative_force_balance_error': float(force_error),
                   'relative_moment_balance_error': float(moment_error),
                   'applied_force_N': applied.sum(axis=0).tolist(), 'reaction_N': reacted.sum(axis=0).tolist(),
                   'applied_moment_Nmm': amoment.tolist(), 'reaction_moment_Nmm': rmoment.tolist(),
                   'minimum_wall_gap_mm': float(gaps.min()), 'wall_contact_nodes': len(active),
                   'volume_mm3': float(volume.sum()), 'max_displacement_mm': float(np.linalg.norm(U, axis=1).max()),
                   'load_compliance_Nmm': float(f@u), 'raw_maximum_principal_tensile_MPa': float(principal[maximum, 2]),
                   'raw_peak_centroid_mm': tc[maximum].tolist(), 'raw_peak_cell_volume_mm3': float(volume[maximum]),
                   'raw_maximum_von_mises_MPa': float(vm.max()), 'patches': {},
                   'elapsed_seconds': time.perf_counter()-start,
                   'status': 'SOLVED WITH EQUILIBRIUM GATES; raw stress refinement and process qualification remain separate.'})
    for label, patch in patches.items():
        nodes = patch.pop('nodes')
        patch['mean_displacement_mm'] = U[nodes].mean(axis=0).tolist()
        patch['maximum_displacement_mm'] = float(np.linalg.norm(U[nodes], axis=1).max())
        patch['minimum_vertical_displacement_mm'] = float(U[nodes, 1].min())
        report['patches'][label] = patch
    report['washer_reactions_N'] = {key: reacted[nodes].sum(axis=0).tolist() for key, nodes in heads.items()}
    np.savez_compressed(args.output.with_name(args.output.name+'-solution.npz'), p=p, t=t, u=U,
                        stress=stress, vm=vm, volume=volume, wall_nodes=wall, active_wall=active,
                        initial_wall_gap=gap0, applied_force=applied, reaction=reacted)
    args.output.with_name(args.output.name+'-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['status', 'max_displacement_mm', 'raw_maximum_principal_tensile_MPa', 'raw_peak_centroid_mm', 'relative_free_residual', 'relative_force_balance_error', 'relative_moment_balance_error', 'elapsed_seconds']}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--load-N', type=float, default=117.72)
    parser.add_argument('--E', type=float, default=1000.)
    parser.add_argument('--nu', type=float, default=.35)
    parser.add_argument('--surface-tolerance-mm', type=float, default=.05)
    parser.add_argument('--solver', choices=['pardiso', 'superlu'], default='pardiso')
    parser.add_argument('--flat-wall-reference', action='store_true')
    parser.add_argument('--interfaces-only', action='store_true')
    solve(parser.parse_args())


if __name__ == '__main__':
    main()
