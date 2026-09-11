"""Shared bounded normal-contact loop for GPU fixtures and actual brackets."""
import time
import numpy as np


def solve_contact(op,f,base,wall,gap0,*,maxiter=5000,max_seconds=240,
                  initial=None,preconditioner_factory=None,progress=lambda x:None,
                  save_state=lambda *x:None,max_steps=40,initial_active=None,
                  linear_rtol=1e-10,true_residual_limit=1e-8):
    start=time.perf_counter()
    base,wall=np.unique(base).astype(int),np.asarray(wall,dtype=int)
    gap0=np.asarray(gap0,dtype=float)
    assert len(wall)==len(gap0) and len(np.unique(wall))==len(wall)
    assert np.all(gap0>=0) and not len(np.intersect1d(base,wall))
    active=np.flatnonzero(gap0<1e-12) if initial_active is None else np.unique(initial_active).astype(int)
    assert np.all((active>=0)&(active<len(wall)))
    history=[]
    for step in range(max_steps):
        fixed=np.union1d(base,wall[active])
        prescribed=np.zeros(op.ndof);prescribed[wall[active]]=-gap0[active]
        M,coarse_report=(None,None) if preconditioner_factory is None else preconditioner_factory(fixed)
        trace=[]
        def observe(iterations,residual,tolerance):
            entry={'stage':'cg','contact_step':step,'iterations':iterations,
                   'residual':residual,'tolerance':tolerance}
            trace.append(entry.copy());progress(entry)
        remaining=max(1.,max_seconds-(time.perf_counter()-start))
        u,r,info=op.solve(f,fixed,prescribed,maxiter,observe,remaining,initial,M,
                        linear_rtol,true_residual_limit)
        initial=u
        gaps=gap0+u[wall]
        info.update({'contact_step':step,'active_wall_nodes':len(active),'trace':trace,
                     'coarse_correction':coarse_report})
        history.append(info)
        save_state(step,u,r,gaps,active,fixed)
        if info['status']!='PASS_LINEAR_SOLVE':
            return u,r,gaps,active,history,info['status']
        next_active=np.flatnonzero(r[wall]-op.diag[wall]*gaps>1e-8)
        progress({'stage':'contact_update','contact_step':step,'active_wall_nodes':len(active),
                  'next_active_wall_nodes':len(next_active),'minimum_gap_mm':float(gaps.min(initial=0)),
                  'minimum_active_reaction_N':float(r[wall[active]].min(initial=0)),
                  'released_nodes':int(len(np.setdiff1d(active,next_active))),
                  'added_nodes':int(len(np.setdiff1d(next_active,active)))})
        if np.array_equal(active,next_active):
            if gaps.min(initial=0)<-1e-8 or r[wall[active]].min(initial=0)<-1e-8:
                status='FAIL_CONTACT_COMPLEMENTARITY'
            else:
                status='PASS_CONTACT_NUMERICS'
            return u,r,gaps,active,history,status
        if step+1<max_steps:
            active=next_active
    return u,r,gaps,active,history,'FAIL_CONTACT_ITERATIONS'
