"""Independent Galerkin and elasticity tests for the coarse correction."""
from pathlib import Path
import argparse,json,time

import numpy as np
from scipy.sparse import eye,kron,diags
from scipy.sparse.linalg import LinearOperator,cg,splu,spsolve

from gpu_demo_geometry import fast_mesh
from gpu_demo_adaptive import coarsen
from gpu_coarse_geometry import build
from validate_gpu_demo_adaptive import independent_fine


def fixture_mesh(shape,spacing=(.25,)*3):
    p,t,cells,_=fast_mesh(shape,np.array(spacing),np.zeros(3))
    a=coarsen(p,t,cells,spacing,(0,0,0),protect=cells[:,0]<3)
    P=kron(a['P'],eye(3,format='csr'),format='csr')
    Af=(P.T @ independent_fine(p,t) @ P).tocsr()
    return p,a,Af


def run(gpu=False):
    report={'status':'RUNNING','geometry_checks':[]}
    fields={}
    for fixture in ['solid','hollow','partial_contact','translated_grid']:
        shape=np.ones((12,4,4),dtype=bool)
        if fixture=='hollow':
            shape[4:,1:3,1:3]=False
        if fixture=='partial_contact':
            shape[6:,2:,:]=False
            shape[6:,3:,3:]=True
        p,a,Af=fixture_mesh(shape,spacing=(.3,.4,.2))
        origin=np.zeros(3)
        if fixture=='translated_grid':
            origin=np.array([-.2,-43.,0.])
            p=p+origin+np.array([640,128,0])*[.3,.4,.2]
        # Mix fully constrained nodes and individual vector components near
        # hanging nodes; scalar masking alone cannot satisfy this test.
        fixed=np.unique(np.r_[np.flatnonzero(np.repeat(np.isclose(p[a['master'],0],p[:,0].min()),3)),
                               np.arange(13,Af.shape[0],37)])
        for ratio in [2,4]:
            A,Q,pc,info=build(p,a['t'],a['scale'],a['P'],a['master'],(.3,.4,.2),origin,ratio,fixed)
            Z=kron(Q,eye(3,format='csr'),format='csr')
            free=np.ones(Af.shape[0]);free[fixed]=0
            Z=Z.multiply(free[:,None]).tocsr()
            expected=(Z.T @ Af @ Z).tocsr()
            inactive=info['identically_zero_projected_coarse_dofs']
            assert not np.any(Z[:,inactive].data)
            auxiliary=np.zeros(A.shape[0]);auxiliary[inactive]=1
            expected += diags(auxiliary)
            error=float(np.max(abs((A-expected).data),initial=0)/np.max(abs(expected.data)))
            assert error<2e-11,(fixture,ratio,error)
            report['geometry_checks'].append({'fixture':fixture,**info,'relative_error_vs_independent_projected_operator':error})
    shape=np.ones((128,4,4),dtype=bool)
    p,a,Af=fixture_mesh(shape)
    pm=p[a['master']]
    fixed=np.flatnonzero(np.repeat(np.isclose(pm[:,0],0.),3))
    free=np.setdiff1d(np.arange(Af.shape[0]),fixed)
    A=Af[free][:,free].tocsr()
    f=np.zeros((len(pm),3));tip=np.isclose(pm[:,0],32.)
    f[tip,1]=-1e-3/tip.sum()
    rhs=f.ravel()[free]
    exact=spsolve(A.tocsc(),rhs)
    diagonal=1/A.diagonal()
    results=[]
    for ratio in [None,4,8]:
        start=time.perf_counter()
        if ratio is None:
            M=LinearOperator(A.shape,matvec=lambda x:diagonal*x)
            info={}
        else:
            Ac,Q,pc,info=build(p,a['t'],a['scale'],a['P'],a['master'],(.25,)*3,(0,)*3,ratio,fixed)
            Z=kron(Q,eye(3,format='csr'),format='csr')[free]
            factor=splu(Ac.tocsc())
            M=LinearOperator(A.shape,matvec=lambda x:diagonal*x+Z @ factor.solve(Z.T @ x))
        setup=time.perf_counter()-start
        trace=[]
        start=time.perf_counter()
        u,flag=cg(A,rhs,M=M,rtol=1e-10,atol=1e-14,maxiter=10000,callback=lambda x:trace.append(float(np.linalg.norm(A @ x-rhs))))
        elapsed=time.perf_counter()-start
        relative=float(np.linalg.norm(A @ u-rhs)/np.linalg.norm(rhs))
        displacement_error=float(np.linalg.norm(u-exact)/np.linalg.norm(exact))
        assert flag==0 and relative<1e-7 and displacement_error<1e-7,(ratio,flag,relative,displacement_error)
        results.append({'ratio':ratio,'iterations':len(trace),'setup_seconds':setup,'solve_seconds':elapsed,
                        'true_relative_residual':relative,'displacement_relative_error_vs_direct_cpu':displacement_error,'trace':trace,**info})
        full=np.zeros(Af.shape[0]);full[free]=u
        fields[str(ratio)+'_master_u']=full
    assert results[1]['iterations'] < results[0]['iterations'],results
    fields['p'],fields['t'],fields['scale']=p,a['t'],a['scale']
    if gpu:
        import warp as wp
        from gpu_demo_adaptive_operator import AdaptiveOperator
        from gpu_multigrid import CoarseCorrection
        op=AdaptiveOperator(a['t'],a['scale'],a['P'],(.25,)*3)
        mg=CoarseCorrection(op,p,a['master'],(0,)*3,4,fixed)
        rng=np.random.default_rng(911)
        vectors=[rng.normal(size=op.ndof) for _ in range(2)]
        applied=[]
        for vector in vectors:
            x=wp.array(vector,dtype=wp.float64,device=op.device)
            out=wp.zeros_like(x)
            mg.operator().matvec(x,out,out,1.,0.)
            actual=out.numpy();expected=mg.cpu_apply(vector)
            error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected))
            assert error<1e-10,error
            assert np.dot(vector,actual)>0
            applied.append(actual)
        symmetry=float(abs(vectors[0] @ applied[1]-vectors[1] @ applied[0])/
                       (np.linalg.norm(vectors[0])*np.linalg.norm(applied[1])+np.linalg.norm(vectors[1])*np.linalg.norm(applied[0])))
        assert symmetry<1e-10,symmetry
        gpu_rows=[]
        for label,preconditioner in [('diagonal',None),('coarse_amg',mg.operator())]:
            u,reaction,info=op.solve(f.ravel(),fixed,maxiter=10000,preconditioner=preconditioner)
            assert info['status']=='PASS_LINEAR_SOLVE',info
            difference=float(np.linalg.norm(u[free]-exact)/np.linalg.norm(exact))
            assert difference<1e-7,difference
            fields[label+'_gpu_master_u']=u
            fields[label+'_gpu_reaction']=reaction
            fields[label+'_gpu_all_stress']=np.concatenate([s for _,s in op.stress_chunks(u)])
            gpu_rows.append({'method':label,'displacement_error_vs_independent_direct':difference,**info})
        assert gpu_rows[1]['iterations']<gpu_rows[0]['iterations']
        report['gpu']={'preconditioner_relative_error_vs_cpu':error,'preconditioner_symmetry_error':symmetry,
                       'coarse_setup':mg.report,'solves':gpu_rows}
    report.update({'status':'PASS','beam_results':results,
                   'scope':'Exact coarse Galerkin operator checked against independent scikit-fem projected operator. CPU preconditioner prototype; full-G and GPU multigrid remain separate gates.'})
    return report,fields


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--gpu',action='store_true')
    args=ap.parse_args();assert not args.output.exists()
    args.output.mkdir(parents=True)
    report,fields=run(args.gpu)
    (args.output/'fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
    np.savez(args.output/'fields.npz',**fields)
    print(json.dumps({k:v for k,v in report.items() if k!='beam_results'},indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!='trace'} for r in report['beam_results']],indent=2))
