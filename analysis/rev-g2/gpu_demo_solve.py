"""Bounded full-G adaptive GPU trial; failures and every stress sample survive."""
from pathlib import Path
import argparse
import hashlib
import json
import time

import numpy as np
from scipy.sparse import load_npz

from gpu_demo_adaptive_operator import AdaptiveOperator
from gpu_hex import stress_tensors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--geometry',type=Path,required=True)
    ap.add_argument('--adaptive',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--maxiter',type=int,default=1000)
    ap.add_argument('--max-seconds',type=float,default=240)
    ap.add_argument('--load',type=float,default=117.72)
    ap.add_argument('--initial',type=Path)
    args = ap.parse_args()
    assert not args.output.exists(),'Use a fresh directory; retain earlier raw attempts'
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    def progress(event):
        event['elapsed_seconds'] = time.perf_counter()-started
        print(json.dumps(event),flush=True)
        (args.output/'progress.json').write_text(json.dumps(event,indent=2)+'\n')
    with np.load(args.geometry/'geometry.npz') as data:
        p,spacing = data['p'],data['spacing']
    with np.load(args.adaptive/'adaptive.npz') as data:
        t,scale,master = [data[k] for k in ['t','scale','master']]
    P = load_npz(args.adaptive/'prolongation.npz')
    mapping = np.full(len(p),-1,dtype=np.int32)
    mapping[master] = np.arange(len(master),dtype=np.int32)
    with np.load(args.geometry/'interfaces.npz') as data:
        f = np.asarray(P.T @ data['f'].reshape(-1,3)).ravel()*(args.load/117.72)
        base_full,wall_full,gap = data['base'],data['wall'],data['gap']
        assert np.all(mapping[base_full//3] >= 0) and np.all(mapping[wall_full] >= 0), 'Refine hardware/contact patches before constraining them'
        base = 3*mapping[base_full//3]+base_full%3
        wall = 3*mapping[wall_full]
    progress({'stage':'loaded','leaf_cells':len(t),'independent_dofs':3*len(master)})
    op = AdaptiveOperator(t,scale,P,spacing)
    progress({'stage':'gpu_setup','setup_seconds':op.setup_seconds})
    active = np.flatnonzero(gap < 1e-12)
    history = []
    status = 'FAIL_CONTACT_ITERATIONS'
    initial = None if args.initial is None else np.load(args.initial)
    for step in range(20):
        fixed = np.union1d(base,wall[active])
        prescribed = np.zeros(op.ndof)
        prescribed[wall[active]] = -gap[active]
        trace = []
        def observe(iterations,residual,tolerance):
            entry = {'stage':'cg','contact_step':step,'iterations':iterations,
                     'residual':residual,'tolerance':tolerance}
            trace.append(entry.copy())
            progress(entry)
        remaining = max(1.,args.max_seconds-(time.perf_counter()-started))
        u,reaction,info = op.solve(f,fixed,prescribed,args.maxiter,observe,remaining,initial)
        initial = u
        info.update({'contact_step':step,'active_wall_nodes':len(active),'trace':trace})
        history.append(info)
        gaps = gap+u[wall]
        # Save every contact iterate, even if its linear solve failed.
        state = args.output/f'contact-{step:02d}'
        state.mkdir()
        for name,values in [('master_u',u),('master_reaction',reaction),('master_force',f),
                            ('wall_gaps',gaps),('active_wall_indices',active),('fixed_dofs',fixed)]:
            np.save(state/(name+'.npy'),values)
        if info['status'] != 'PASS_LINEAR_SOLVE':
            status = info['status']
            break
        next_active = np.flatnonzero(reaction[wall]-op.diag[wall]*gaps > 1e-8)
        if np.array_equal(active,next_active):
            assert gaps.min() >= -1e-8
            assert not len(active) or reaction[wall[active]].min() >= -1e-8
            status = 'PASS_CONTACT_NUMERICS_ERODED_MATERIAL_ONLY'
            break
        active = next_active
    progress({'stage':'recovering_all_stress','status':status})
    manifest = []
    tensile,vm = -float('inf'),0.
    for begin,stress in op.stress_chunks(u):
        path = args.output/f'stress-{begin:08d}.npy'
        np.save(path,stress)
        principal = np.linalg.eigvalsh(stress_tensors(stress))
        tensile = max(tensile,float(principal[:,:,-1].max()))
        equivalent = np.sqrt(((principal[:,:,0]-principal[:,:,1])**2+
                              (principal[:,:,1]-principal[:,:,2])**2+
                              (principal[:,:,2]-principal[:,:,0])**2)/2)
        vm = max(vm,float(equivalent.max()))
        manifest.append({'file':path.name,'first_leaf':begin,'cells':len(stress),
                         'gauss_samples':len(stress)*8,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    total_force = f.reshape(-1,3).sum(axis=0)
    total_reaction = reaction.reshape(-1,3).sum(axis=0)
    full_u = P @ u.reshape(-1,3)
    report = {'status':status,'load_N':args.load,'leaf_cells':len(t),'independent_nodes':len(master),
              'planning_E_MPa':1000.,'planning_nu':.35,
              'raw_tensile_peak_MPa':tensile,'raw_von_mises_peak_MPa':vm,
              'maximum_resultant_displacement_mm':float(np.linalg.norm(full_u,axis=1).max()),
              'total_applied_force_N':total_force.tolist(),'total_raw_residual_force_N':total_reaction.tolist(),
              'minimum_wall_gap_mm':float(gaps.min()),'contact_history':history,
              'stress_fields':manifest,'every_leaf_retained':sum(m['cells'] for m in manifest) == len(t),
              'elapsed_seconds':time.perf_counter()-started,
              'interpretation':'A failed linear/contact iterate is not a movement or strength prediction. Even passing numerics use eroded reference slice geometry, unmeasured isotropic properties and idealized hardware. No full-bracket qualification.'}
    (args.output/'solve.json').write_text(json.dumps(report,indent=2)+'\n')
    progress({'stage':'complete','status':status,'raw_tensile_peak_MPa':tensile,'elapsed_total_seconds':report['elapsed_seconds']})


if __name__ == '__main__':
    main()
