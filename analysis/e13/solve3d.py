"""E13 small-strain isotropic 3D FEM, constant-strain tetrahedra.
N, mm, MPa. Sparse infill has already been removed from the analysis-only mesh.
E=1000 MPa reference: displacement scales inversely with E, stress does not.
"""
from pathlib import Path
import sys,json,time,os
os.environ.setdefault('MKL_NUM_THREADS','8')
import numpy as np
from scipy.sparse.linalg import cg,splu
import pyamg
from skfem import MeshTet,Basis,ElementTetP1,ElementVector,asm
from skfem.models.elasticity import linear_elasticity
D=Path(__file__).resolve().parent
name=sys.argv[1];d=np.load(D/f'{name}.npz');p=d['p'];t=d['t'];N=len(p)
m=MeshTet(p.T,t.T);basis=Basis(m,ElementVector(ElementTetP1()))
E=1000.;nu=.35;mu=E/(2*(1+nu));lam=E*nu/((1+nu)*(1-2*nu))
print('assemble',name,N,len(t),flush=True);K=asm(linear_elasticity(lam,mu),basis).tocsr()
f=np.zeros(3*N);bf=m.boundary_facets();tri=m.facets[:,bf].T;v=p[tri];cent=v.mean(1);area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
fix=[];patches={}
def patch(mask,force,label):
 ids=tri[mask];a=area[mask];assert len(ids)>0,label
 w=a/a.sum()/3
 for j in range(3):
  for q in range(3):np.add.at(f,3*ids[:,j]+q,w*force[q])
 patches[label]={'area_mm2':float(a.sum()),'facets':int(mask.sum()),'force_N':list(force),'nodes':np.unique(ids)}
 return mask
if name.startswith('landing'):
 rr=np.hypot(cent[:,1]-164,cent[:,2]-12)
 mask=(abs(cent[:,0]-3.6)<1e-5)&(rr>2.75)&(rr<6.5)
 patch(mask,[-500.,0.,0.],'washer')
 wall=np.where(abs(p[:,0])<1e-5)[0];fix.extend(3*wall)
 # Minimal lateral restraints remove rigid translation/rotation while allowing Poisson expansion.
 a=wall[np.argmin((p[wall,1]-154)**2+(p[wall,2]-12)**2)];b=wall[np.argmin((p[wall,1]-174)**2+(p[wall,2]-12)**2)]
 fix.extend([3*a+1,3*a+2,3*b+2]);contact=False
else:
 S=np.hypot(100,12);q=np.sqrt((90+12.4)**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S;aa=cx-90;bb=190-cx;den=aa*(cy-12)+bb*cy;H=117.72*aa*bb/den;Vrear=117.72*bb*cy/den;Vfront=117.72*aa*(cy-12)/den
 for x,sgn,label in [(90,-1,'rear_seat'),(190,1,'front_seat')]:
  yy=0 if x==90 else 12;V=Vrear if x==90 else Vfront
  r=np.hypot(cent[:,0]-x,cent[:,1]-yy);theta=np.arctan2(cent[:,1]-yy,cent[:,0]-x);target=np.arctan2(-V,sgn*H)
  da=np.arctan2(np.sin(theta-target),np.cos(theta-target))
  mask=(abs(r-13)<.12)&(abs(da)<np.deg2rad(25))
  patch(mask,[sgn*H,-V,0.],label)
 for y in [164,40]:
  r=np.hypot(p[:,1]-y,p[:,2]-12)
  head=np.where((abs(p[:,0]-3.6)<1e-5)&(r>2.75)&(r<6.5))[0]
  bore=np.where((p[:,0]<3.61)&(abs(r-2.6)<.06))[0]
  assert len(head)>0 and len(bore)>0
  fix.extend(3*head);fix.extend(3*bore+1);fix.extend(3*bore+2)
 wall=np.where(abs(p[:,0])<1e-5)[0];contact=True
base=np.unique(fix).astype(int);active=wall.copy();u=np.zeros(3*N)
# Rigid modes improve algebraic multigrid on an unconstrained elasticity operator.
B=np.zeros((3*N,6));B[0::3,0]=1;B[1::3,1]=1;B[2::3,2]=1
q=p-p.mean(0);B[1::3,3]=-q[:,2];B[2::3,3]=q[:,1];B[0::3,4]=q[:,2];B[2::3,4]=-q[:,0];B[0::3,5]=-q[:,1];B[1::3,5]=q[:,0]
# Warm-start from the nearest completed coarser mesh of this exact domain.
current_h=float(name.rsplit('-h',1)[1]);prefix=name.split('-h')[0]
candidates=[q for q in D.glob(prefix+'-h*-solution.npz') if float(q.name.split('-h')[1].split('-solution')[0])>current_h]
coarse=min(candidates,key=lambda q:float(q.name.split('-h')[1].split('-solution')[0])) if candidates else None
if contact and coarse is None and name.startswith('baseline-e12-'):
 archived=D.parent/'e12'/(name.removeprefix('baseline-e12-').split('-h')[0]+'-h2-solution.npz')
 if archived.exists():coarse=archived
if contact and coarse is not None:
 from scipy.spatial import cKDTree
 old=np.load(coarse)
 if 'active_wall' in old:
  ow=old['wall_nodes'];oi=cKDTree(old['p'][ow]).query(p[wall])[1]
  active=wall[np.isin(ow[oi],old['active_wall'])]
its=[];converged=False
for it in range(30):
 fixed=np.union1d(base,3*active) if contact else base;free=np.setdiff1d(np.arange(3*N),fixed)
 A=K[free][:,free];rhs=f[free]
 count=[0]
 def cb(x):count[0]+=1
 if '--pardiso' in sys.argv:
  from pypardiso import PyPardisoSolver
  factor=PyPardisoSolver();factor.factorize(A)
  sol=factor.solve(A,rhs)
  for refinement in range(5):sol+=factor.solve(A,rhs-A@sol)
  factor.free_memory(everything=True)
  info=0;count[0]=-2
 elif '--direct' in sys.argv:
  # Symmetric minimum-degree ordering keeps fill manageable for thin domains.
  factor=splu(A.tocsc(),permc_spec='MMD_AT_PLUS_A',options={'Equil':True})
  sol=factor.solve(rhs)
  for refinement in range(3):sol+=factor.solve(rhs-A@sol)
  info=0;count[0]=-1
 else:
  ml=pyamg.smoothed_aggregation_solver(A,B=B[free],symmetry='symmetric',max_coarse=150)
  sol,info=cg(A,rhs,x0=u[free],M=ml.aspreconditioner(),rtol=2e-9,atol=1e-10,maxiter=2500,callback=cb)
 assert info==0,(it,info)
 u[:]=0;u[free]=sol;r=K@u-f
 its.append(count[0]);print('solve',it,count[0],'free',len(free),flush=True)
 if not contact:converged=True;break
 # Primal-dual active set for frictionless wall: u_x >= 0, reaction_x >= 0.
 new=wall[(r[3*wall]-K.diagonal()[3*wall]*u[3*wall])>1e-7]
 if np.array_equal(new,active):converged=True;break
 print('contact',len(active),'->',len(new),'min gap',u[3*wall].min(),'min R',r[3*wall].min(),flush=True);active=new
assert converged,'Contact active set failed'
true_residual=float(np.linalg.norm(r[free])/np.linalg.norm(f[free]))
assert true_residual < 1e-6, f'Independent assembled residual failed: {true_residual}'
U=u.reshape(-1,3);field=basis.interpolate(u);grad=field.grad.mean(axis=-1);strain=(grad+grad.transpose(1,0,2))/2
stress=2*mu*strain+lam*np.einsum('iie->e',strain)[None,None,:]*np.eye(3)[:,:,None]
dev=stress-np.einsum('iie->e',stress)[None,None,:]*np.eye(3)[:,:,None]/3;vm=np.sqrt(1.5*np.einsum('ije,ije->e',dev,dev))
principal=np.linalg.eigvalsh(stress.transpose(2,0,1));vol=basis.dx.sum(1);tc=p[t].mean(1)
def weighted_quantile(values,weights,quantile):
 ii=np.argsort(values);return float(np.interp(quantile*np.sum(weights),np.cumsum(weights[ii]),values[ii]))
res={'name':name,'nodes':N,'tetrahedra':len(t),'E_reference_MPa':E,'nu':nu,'contact_converged':converged,'linear_iterations':its,'volume_mm3':float(vol.sum()),'applied_force_N':f.reshape(-1,3).sum(0).tolist(),'reaction_N':r.reshape(-1,3).sum(0).tolist(),'applied_moment_Nmm':np.cross(p,f.reshape(-1,3)).sum(0).tolist(),'reaction_moment_Nmm':np.cross(p,r.reshape(-1,3)).sum(0).tolist(),'relative_free_residual':float(np.linalg.norm(r[free])/np.linalg.norm(f[free])),'max_displacement_mm_at_E1000':float(np.linalg.norm(U,axis=1).max()),'vm_max_MPa_not_allowable':float(vm.max()),'vm_volume_p99_MPa':weighted_quantile(vm,vol,.99),'vm_volume_p999_MPa':weighted_quantile(vm,vol,.999),'patches':{}}
res['relative_force_balance_error']=float(np.linalg.norm(np.array(res['applied_force_N'])+res['reaction_N'])/max(1.,np.linalg.norm(res['applied_force_N'])))
res['linear_solver']='PARDISO with five residual-correction solves' if '--pardiso' in sys.argv else ('SuperLU with three residual-correction solves' if '--direct' in sys.argv else 'AMG-preconditioned CG')
res['relative_moment_balance_error']=float(np.linalg.norm(np.array(res['applied_moment_Nmm'])+res['reaction_moment_Nmm'])/max(1.,np.linalg.norm(res['applied_moment_Nmm'])))
assert res['relative_force_balance_error']<1e-6 and res['relative_moment_balance_error']<1e-6,res
res['wall_minimum_gap_mm']=float(U[wall,0].min())
res['wall_contact_nodes']=int(len(active))
for label,pa in patches.items():
 nodes=pa.pop('nodes');pa['mean_displacement_mm_at_E1000']=U[nodes].mean(0).tolist();res['patches'][label]=pa
for y in [164,40]:
 mask=(abs(p[:,0]-3.6)<1e-5)&(np.hypot(p[:,1]-y,p[:,2]-12)<6.5)
 res[f'head_{y}_reaction_N']=r.reshape(-1,3)[mask].sum(0).tolist()
regions={'rear_seat':(tc[:,0]>75)&(tc[:,0]<110)&(tc[:,1]<0),'forearm':(tc[:,0]>110)&(tc[:,0]<170),'upper_landing':(tc[:,0]<10)&(abs(tc[:,1]-164)<9),'lower_landing':(tc[:,0]<10)&(abs(tc[:,1]-40)<9),'knee':(tc[:,0]>30)&(tc[:,0]<75)&(tc[:,1]<40)}
regions['near_rear_seat_fixed_window']=(tc[:,0]>75)&(tc[:,0]<110)&(tc[:,1]<0)&(tc[:,1]>-24)
res['regions']={}
for key,mask in regions.items():
 if mask.any():res['regions'][key]={'vm_p99_MPa':weighted_quantile(vm[mask],vol[mask],.99),'vm_max_MPa':float(vm[mask].max()),'max_principal_MPa':float(principal[mask,2].max())}
np.savez_compressed(D/f'{name}-solution.npz',p=p,t=t,u=U,vm=vm,stress=stress,volume=vol,wall_nodes=wall,active_wall=active)
(D/f'{name}-results.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2),flush=True)
