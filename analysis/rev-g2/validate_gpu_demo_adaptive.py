"""Independent mechanics checks for the two-level nonconforming hex mesh."""
from pathlib import Path
import argparse
import json

import numpy as np
from scipy.sparse import coo_matrix, eye, kron
from scipy.sparse.linalg import spsolve
from skfem import Basis, MeshHex, ElementHex1, ElementVector, asm
from skfem.models.elasticity import linear_elasticity

from gpu_hex import element
from gpu_demo_geometry import fast_mesh
from gpu_demo_adaptive import coarsen


def assemble_leaf(t,scale,n,spacing):
    ke,_,_,_ = element(spacing)
    dofs = (3*t[:,:,None]+np.arange(3)).reshape(-1,24)
    rows = np.broadcast_to(dofs[:,:,None],(len(t),24,24)).ravel()
    cols = np.broadcast_to(dofs[:,None,:],(len(t),24,24)).ravel()
    return coo_matrix(((scale[:,None,None]*ke).ravel(),(rows,cols)),shape=(3*n,3*n)).tocsr()


def independent_fine(p,t):
    # scikit-fem's local cube order differs from the VTK/our order.
    order = [0,1,3,4,2,5,7,6]
    mesh = MeshHex(p.T,t[:,order].T)
    basis = Basis(mesh,ElementVector(ElementHex1()),intorder=2)
    return asm(linear_elasticity(1000*.35/(1.35*.3),1000/2.7),basis).tocsr()


def run(gpu=False):
    rng = np.random.default_rng(9126)
    checks,fields = [],{}
    for name in ['transition','hollow','edge_corner','partial_edge_bridge']:
        occupancy = np.ones((12,4,4),dtype=bool)
        if name == 'hollow':
            occupancy[:,1:3,1:3] = False
            occupancy[:4] = True
        if name == 'edge_corner':
            occupancy = np.zeros((8,8,8),dtype=bool)
            occupancy[:4,:4,:4] = True
            occupancy[4:6,4:6,:2] = True  # Edge-only contact.
            occupancy[4:6,4:6,4:6] = True  # Separate corner touch.
        if name == 'partial_edge_bridge':
            occupancy = np.zeros((4,4,2),dtype=bool)
            occupancy[:2,:2,:] = True
            occupancy[2:,2:,:] = True
            occupancy[1,2,0] = True  # A real face connection over half an edge.
        p,t,cells,_ = fast_mesh(occupancy,np.array([.3,.4,.2]),np.zeros(3))
        result = coarsen(p,t,cells,(.3,.4,.2),(0,0,0),protect=cells[:,0] >= 5)
        P = kron(result['P'],eye(3,format='csr'),format='csr')
        leaf = assemble_leaf(result['t'],result['scale'],len(p),(.3,.4,.2))
        fine = independent_fine(p,t)
        reduced = P.T @ leaf @ P
        reference = P.T @ fine @ P
        error = np.max(abs((reduced-reference).data))/np.max(abs(reference.data))
        assert error < 1e-12,(name,error)
        # A random field probes every hanging-node constraint, not just affine
        # reproduction. Equality follows because the coarse Q1 space embeds
        # exactly in the fine space over the same fully filled blocks.
        u = rng.normal(size=reduced.shape[0])
        energy_error = abs(u @ reduced @ u-u @ reference @ u)/abs(u @ reference @ u)
        assert energy_error < 1e-12
        pm = p[result['master']]
        rigid = np.cross(np.tile([.03,-.04,.02],(len(pm),1)),pm)+[.1,.2,.3]
        rigid_error = np.linalg.norm(reduced @ rigid.ravel())/(np.linalg.norm(reduced.data)*np.linalg.norm(rigid))
        assert rigid_error < 1e-13
        checks.append({'fixture':name,**result['report'],
                       'independent_projected_operator_relative_error':float(error),
                       'random_energy_relative_error':float(energy_error),
                       'rigid_relative_residual':float(rigid_error)})
        if gpu:
            from gpu_demo_adaptive_operator import AdaptiveOperator
            op = AdaptiveOperator(result['t'],result['scale'],result['P'],(.3,.4,.2))
            actual = op.apply(u)
            relative = np.linalg.norm(actual-reference @ u)/np.linalg.norm(reference @ u)
            assert relative < 1e-12,(name,relative)
            fixed = np.flatnonzero(np.arange(len(u))%11 == 0)
            test = u.copy()
            test[fixed] = 0
            expected = reference @ test
            expected[fixed] = u[fixed]
            projected = np.linalg.norm(op.apply(u,fixed)-expected)/np.linalg.norm(expected)
            assert projected < 1e-12
            checks[-1]['gpu_operator_relative_error'] = float(relative)
            checks[-1]['gpu_dirichlet_operator_relative_error'] = float(projected)
            fields[name+'_random_stress'] = np.concatenate([s for _,s in op.stress_chunks(u)])
            gradient = np.array([[.001,.002,-.0003],[.0007,-.0004,.0002],[.0003,-.0005,.0006]])
            affine = (pm @ gradient.T).ravel()
            affine_stress = np.concatenate([s for _,s in op.stress_chunks(affine)])
            strain = [gradient[0,0],gradient[1,1],gradient[2,2],gradient[0,1]+gradient[1,0],
                      gradient[1,2]+gradient[2,1],gradient[0,2]+gradient[2,0]]
            expected_stress = op.C @ strain
            stress_error = float(np.max(abs(affine_stress-expected_stress)))
            assert stress_error < 1e-10
            checks[-1]['affine_all_gauss_stress_max_error_MPa'] = stress_error
            fields[name+'_affine_stress'] = affine_stress
        fields[name+'_p'] = p
        fields[name+'_t'] = result['t']
        fields[name+'_scale'] = result['scale']
        fields[name+'_random_displacement'] = np.asarray(P @ u).reshape(-1,3)
    # Long thin beam: a mixed mesh must converge to the uniform fine result,
    # and cannot become more compliant than its parent fine FE space.
    occupancy = np.ones((64,4,4),dtype=bool)
    p,t,cells,_ = fast_mesh(occupancy,np.array([.25,.25,.25]),np.zeros(3))
    fine = independent_fine(p,t)
    f = np.zeros_like(p)
    tip = np.isclose(p[:,0],16.)
    f[tip,1] = -1/np.count_nonzero(tip)
    results = []
    for protected_length in [0.,4.,8.,12.,16.]:
        a = coarsen(p,t,cells,(.25,)*3,(0,)*3,protect=cells[:,0]*.25 < protected_length)
        P = kron(a['P'],eye(3,format='csr'),format='csr')
        A = P.T @ assemble_leaf(a['t'],a['scale'],len(p),(.25,)*3) @ P
        fm = P.T @ f.ravel()
        fixed = np.repeat(np.isclose(p[a['master'],0],0.),3)
        free = np.flatnonzero(~fixed)
        u = np.zeros(len(fm))
        u[free] = spsolve(A[free][:,free].tocsc(),fm[free])
        if gpu and protected_length == 8.:
            from gpu_demo_adaptive_operator import AdaptiveOperator
            op = AdaptiveOperator(a['t'],a['scale'],a['P'],(.25,)*3)
            gpu_u,reaction,solve_info = op.solve(fm,np.flatnonzero(fixed),maxiter=10000,initial=.7*u)
            assert solve_info['status'] == 'PASS_LINEAR_SOLVE',solve_info
            difference = np.linalg.norm(gpu_u-u)/np.linalg.norm(u)
            assert difference < 1e-7,difference
            solve_info['displacement_relative_error_vs_direct_cpu'] = float(difference)
            fields['beam_gpu_master_displacement'] = gpu_u
            fields['beam_gpu_master_reaction'] = reaction
            fields['beam_gpu_leaf_t'] = a['t']
            fields['beam_gpu_leaf_scale'] = a['scale']
            fields['beam_gpu_all_stress'] = np.concatenate([s for _,s in op.stress_chunks(gpu_u)])
        lifted = (P @ u).reshape(-1,3)
        compliance = float(f.ravel() @ lifted.ravel())
        results.append({'protected_root_length_mm':protected_length,'cells':len(a['t']),
                        'compliance_Nmm':compliance,'tip_mean_y_mm':float(lifted[tip,1].mean())})
        fields['beam_'+str(int(protected_length))+'_displacement'] = lifted
    assert np.all(np.diff([r['compliance_Nmm'] for r in results]) >= -1e-8)
    assert results[-1]['cells'] == len(t)
    fields['beam_p'],fields['beam_fine_t'] = p,t
    return {'status':'PASS','scope':'Independent scikit-fem fine operator equals constrained adaptive operator; nested thin-beam refinement. No whole-G load or contact result.',
            'checks':checks,'thin_beam_refinement':results,
            'gpu_thin_beam_solve':solve_info if gpu else None},fields


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--gpu',action='store_true')
    args = ap.parse_args()
    assert not args.output.exists(),'Retain earlier evidence'
    args.output.mkdir(parents=True)
    report,fields = run(args.gpu)
    (args.output/'fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(args.output/'fields.npz',**fields)
    print(json.dumps(report,indent=2),flush=True)
