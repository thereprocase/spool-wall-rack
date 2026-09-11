"""Analytic opening/closing/release fixtures for the production GPU loop."""
from pathlib import Path
import argparse,json
import numpy as np

from gpu_demo_geometry import fast_mesh
from gpu_demo_adaptive import coarsen
from gpu_demo_adaptive_operator import AdaptiveOperator
from gpu_multigrid import CoarseCorrection
from gpu_contact import solve_contact
from validate_gpu_hex import face_load,equilibrium


def run():
    p,t,cells,_=fast_mesh(np.ones((8,2,2),dtype=bool),np.array([.5]*3),np.zeros(3))
    a=coarsen(p,t,cells,(.5,)*3,(0,)*3,protect=(cells[:,0]<2)|(cells[:,0]>=6))
    pm=p[a['master']]
    op=AdaptiveOperator(a['t'],a['scale'],a['P'],(.5,)*3)
    base=np.r_[3*np.flatnonzero(pm[:,0]==4),3*np.flatnonzero(pm[:,1]==0)+1,3*np.flatnonzero(pm[:,2]==0)+2]
    wall=3*np.flatnonzero(pm[:,0]==0)
    rows=[];fields={'p':p,'t':a['t'],'scale':a['scale'],'master':a['master']}
    def factory(fixed):
        mg=CoarseCorrection(op,p,a['master'],(0,)*3,2,fixed)
        return mg.operator(),mg.report
    initial,initial_active=None,None
    for name,total,gap in [('open',-2.,.02),('closed',-10.,.02),('touching_closed',-2.,0.),('release',2.,0.),('exactly_touching',-5.,.02)]:
        ff=face_load(p,t,(.5,)*3,0.,[total,0.,0.])
        ff *= abs(total/ff.sum())
        f=np.asarray(a['P'].T @ ff.reshape(-1,3)).ravel()
        u,r,gaps,active,history,status=solve_contact(op,f,base,wall,np.full(len(wall),gap),preconditioner_factory=factory,
                        initial=initial,initial_active=initial_active)
        initial,initial_active=u.copy(),active.copy()
        expected_u=max(total*4/1000,-gap)
        expected_r=max(-gap*1000/4-total,0)
        error=float(np.max(abs(u[wall]-expected_u)))
        free=np.setdiff1d(np.arange(op.ndof),np.union1d(base,wall[active]))
        balance=equilibrium(pm,f,r,free)
        assert status=='PASS_CONTACT_NUMERICS' and error<1e-9 and abs(r[wall].sum()-expected_r)<1e-7,(name,status,error)
        assert max(balance.values())<1e-7,balance
        rows.append({'name':name,'status':status,'displacement_error_mm':error,'reaction_error_N':float(abs(r[wall].sum()-expected_r)),
                     'minimum_gap_mm':float(gaps.min()),'history':history,'equilibrium':balance})
        for key,value in [('u',u),('reaction',r),('force',f),('gaps',gaps),('active',active),
                           ('all_stress',np.concatenate([s for _,s in op.stress_chunks(u)]))]:
            fields[name+'_'+key]=value
    assert len(rows[3]['history'])>=2
    return {'status':'PASS','cases':rows,'scope':'Analytic 3D frictionless contact with a nonzero gap, prescribed contact displacements and active-node release using the same loop as full G. Consecutive changed-load cases warm-start displacement and contact sets, but solve each load afresh.'},fields


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    report,fields=run()
    (args.output/'fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(args.output/'fields.npz',**fields)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
