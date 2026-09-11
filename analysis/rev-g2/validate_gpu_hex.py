"""Independent analytic and scikit-fem checks of the CUDA hex adapter."""
from pathlib import Path
from itertools import product
import argparse
import json
import time

import numpy as np
import warp as wp
from scipy.sparse.linalg import spsolve
from skfem import MeshHex, Basis, ElementHex1, ElementVector, asm
from skfem.models.elasticity import linear_elasticity

from gpu_hex import HexOperator, mesh_from_cells, stress_tensors
from gpu_benchmark import MemorySampler


def independent_matrix(p,t):
    # scikit-fem reference-cube ordering differs from conventional VTK ordering.
    mesh = MeshHex(p.T, t[:,[0,4,3,1,7,5,2,6]].T)
    basis = Basis(mesh, ElementVector(ElementHex1()), intorder=3)
    E,nu = 1000.,.35
    K = asm(linear_elasticity(E*nu/((1+nu)*(1-2*nu)),E/(2*(1+nu))),basis).tocsr()
    assert np.array_equal(basis.nodal_dofs.T.ravel(), np.arange(p.size))
    return K,basis


def face_load(p,t,spacing,x,force):
    f = np.zeros(p.size)
    for row in t:
        ids = row[np.isclose(p[row,0],x,rtol=0,atol=1e-10)]
        if len(ids) == 4:
            for axis in range(3):
                np.add.at(f,3*ids+axis,np.asarray(force)[axis]/4)
    return f


def equilibrium(p,f,r,free):
    force = float(np.linalg.norm((f+r).reshape(-1,3).sum(axis=0)))
    moment = float(np.linalg.norm(np.cross(p,(f+r).reshape(-1,3)).sum(axis=0)))
    residual = float(np.linalg.norm(r[free])/max(np.linalg.norm(f),1.))
    return {"force_error_N":force,"moment_error_Nmm":moment,"relative_free_residual":residual}


def save_fields(out,name,p,t,u,f,r,stress,spacing,**extra):
    principal = np.linalg.eigvalsh(stress_tensors(stress))
    np.savez_compressed(out/(name+'.npz'),p=p,t=t,u=u.reshape(-1,3),
                        applied_force=f.reshape(-1,3),reaction=r.reshape(-1,3),
                        stress_voigt=stress,principal=principal,
                        volume=np.full(len(t),np.prod(spacing)),**extra)
    return {"cells":len(t),"nodes":len(p),"finite_stress_samples":int(np.prod(stress.shape[:2])),
            "raw_maximum_principal_MPa":float(principal[...,2].max()),
            "maximum_displacement_mm":float(np.linalg.norm(u.reshape(-1,3),axis=1).max())}


def affine(out):
    spacing = (.7,.4,.2)
    p,t,topology = mesh_from_cells(list(product(range(3),range(2),range(2))),spacing)
    op = HexOperator(p,t,spacing)
    K,basis = independent_matrix(p,t)
    A = np.array([[.010,.003,-.002],[.003,-.004,.001],[-.002,.001,.006]])
    u = (p@A.T+[.7,-.2,.4]).ravel()
    sig = 1000/1.35*A+1000*.35/(1.35*.3)*np.trace(A)*np.eye(3)
    stress = op.stress(u)
    error = float(np.abs(stress_tensors(stress)-sig).max())
    energy = .5 * u @ op.apply(u)
    expected = .5*np.prod(spacing)*len(t)*np.sum(sig*A)
    rng = np.random.default_rng(3919)
    trial = rng.normal(size=p.size)
    independent_error = float(np.linalg.norm(op.apply(trial)-K@trial)/np.linalg.norm(K@trial))
    rotation = np.array([[0,-.3,.2],[.3,0,-.1],[-.2,.1,0]])
    rigid_errors = [float(np.linalg.norm(op.apply(np.tile([.2,-.4,.1],len(p))))),
                    float(np.linalg.norm(op.apply((p@rotation.T).ravel())))]
    fields = save_fields(out,'affine',p,t,u,op.apply(u),np.zeros_like(u),stress,spacing)
    assert error < 1e-9 and abs(energy-expected) < 1e-10
    assert independent_error < 1e-12 and max(rigid_errors) < 1e-9
    return {"status":"PASS","stress_max_error_MPa":error,"energy_Nmm":energy,
            "analytic_energy_Nmm":expected,"independent_matrix_relative_error":independent_error,
            "rigid_internal_force_norms_N":rigid_errors,**fields,**topology}


def hollow(out):
    # Exactly 0.4 mm walls, two cells through each wall; no cells in cavity.
    spacing = (.4,.2,.2)
    cells = [c for c in product(range(10),range(8),range(6)) if c[1] < 2 or c[1] >= 6 or c[2] < 2 or c[2] >= 4]
    p,t,topology = mesh_from_cells(cells,spacing)
    op = HexOperator(p,t,spacing)
    fixed = (3*np.flatnonzero(np.isclose(p[:,0],0))[:,None]+np.arange(3)).ravel()
    f = face_load(p,t,spacing,p[:,0].max(),[0.,-1.,0.])
    f /= abs(f.sum())
    u,r,solve = op.solve(f,fixed)
    K,basis = independent_matrix(p,t)
    free = np.setdiff1d(np.arange(p.size),fixed)
    reference = np.zeros(p.size)
    reference[free] = spsolve(K[free][:,free],f[free])
    relative = float(np.linalg.norm(u-reference)/np.linalg.norm(reference))
    balance = equilibrium(p,f,r,free)
    fields = save_fields(out,'hollow-bending',p,t,u,f,r,op.stress(u),spacing,cpu_u=reference.reshape(-1,3))
    assert relative < 1e-8 and max(balance.values()) < 1e-7
    assert len(cells) == 400  # 10 * (8*6 - 4*2); cavity dimensions are 0.8 x 0.4 mm.
    return {"status":"PASS","wall_thickness_mm":.4,"cells_through_wall":2,
            "void_stiffness":0,"independent_displacement_relative_error":relative,
            **balance,**solve,**fields,**topology}


def contact(out):
    spacing = (.5,.5,.5)
    p,t,topology = mesh_from_cells(list(product(range(8),range(2),range(2))),spacing)
    op = HexOperator(p,t,spacing)
    base = np.r_[3*np.flatnonzero(p[:,0] == 4),
                 3*np.flatnonzero(p[:,1] == 0)+1,3*np.flatnonzero(p[:,2] == 0)+2]
    wall = 3*np.flatnonzero(p[:,0] == 0)
    records = []
    for name,total,gap in [('open',-2.,.02),('closed',-10.,.02),('touching_closed',-2.,0.),
                           ('release',2.,0.),('exactly_touching',-5.,.02)]:
        f = face_load(p,t,spacing,0.,[total,0.,0.])
        f *= abs(total/f.sum())
        u,r,gaps,active,history = op.contact(f,base,wall,np.full(len(wall),gap))
        expected_u = max(total*4/1000,-gap)
        expected_reaction = max(-gap*1000/4-total,0)
        error = float(np.max(np.abs(u[wall]-expected_u)))
        reacted = float(r[wall].sum())
        free = np.setdiff1d(np.arange(p.size),np.union1d(base,wall[active]))
        balance = equilibrium(p,f,r,free)
        fields = save_fields(out,'contact-'+name,p,t,u,f,r,op.stress(u),spacing,
                             wall_dofs=wall,initial_gap=np.full(len(wall),gap),final_gap=gaps,active=active)
        records.append({"name":name,"expected_displacement_mm":expected_u,
                        "max_displacement_error_mm":error,"expected_reaction_N":expected_reaction,
                        "reaction_N":reacted,"minimum_gap_mm":float(gaps.min()),
                        "history":history,**balance,**fields})
        assert error < 1e-9 and abs(reacted-expected_reaction) < 1e-7
        assert max(balance.values()) < 1e-7
    assert len(records[3]['history']) >= 2  # touching nodes must actually release
    return {"status":"PASS","cases":records,**topology}


def no_false_bonds():
    results = []
    for shift in [(1,0,0),(1,1,0),(1,1,1),(2,0,0)]:
        p,t,topology = mesh_from_cells([[0,0,0],shift],(.2,.2,.2))
        shared = len(np.intersect1d(t[0],t[1]))
        assert shared == (4 if shift == (1,0,0) else 0)
        results.append({"cell_offset":shift,"shared_nodes":shared,**topology})
    return {"status":"PASS","cases":results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=Path('analysis/rev-g2/gpu-validation'))
    args = ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    wp.init()
    start = time.perf_counter()
    report = {"status":"INCOMPLETE","warp_version":wp.__version__,"device":wp.get_device('cuda:0').name}
    try:
        with MemorySampler() as memory:
            report['no_false_bonds'] = no_false_bonds()
            report['affine'] = affine(args.output)
            report['hollow'] = hollow(args.output)
            report['contact'] = contact(args.output)
        report['memory'] = memory.report()
        report['warp_cuda_mempool_used_high_bytes'] = wp.get_mempool_used_mem_high('cuda:0')
        report['status'] = 'PASS'
    finally:
        report['elapsed_seconds'] = time.perf_counter()-start
        report['scope'] = 'Small 3D isotropic elastic numerical fixtures only. No actual G bracket result or material/process qualification.'
        (args.output/'hex-fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
