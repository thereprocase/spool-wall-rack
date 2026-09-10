"""Plane-stress FEM of projected E8 outline; integrated ideal print thickness.
This independent reduced model omits broad-face chamfers and projects the washer
restraint onto the wall; use 3D for landings and final deformation screening.
"""
from pathlib import Path
import sys,json
import numpy as np
import gmsh
from shapely.geometry import Polygon
from shapely import contains_xy
from scipy.sparse.linalg import spsolve
from skfem import MeshTri,Basis,ElementVector,ElementTriP1,BilinearForm,asm
from skfem.helpers import ddot,sym_grad,trace
D=Path(__file__).resolve().parent;SRC=D.parents[1]/'designs/closed-wall-e8';sys.path.insert(0,str(SRC))
import build_step as b
from fastener_geometry import access_profile
n=int(sys.argv[1]);h=float(sys.argv[2]);name=f'plane-{n}w-h{h:g}';poly=Polygon(b.read_polys('profile.svg')[0]);w=.42+(n-1)*(.45-.2*(1-np.pi/4));core=poly.buffer(-w,quad_segs=12)
gmsh.initialize();gmsh.model.add(name)
ids=[gmsh.model.geo.addPoint(x,y,0,h) for x,y in list(poly.exterior.coords)[:-1]];lines=[gmsh.model.geo.addLine(a,c) for a,c in zip(ids,ids[1:]+ids[:1])];loop=gmsh.model.geo.addCurveLoop(lines);gmsh.model.geo.addPlaneSurface([loop]);gmsh.model.geo.synchronize();gmsh.option.setNumber('Mesh.MeshSizeMin',.35);gmsh.option.setNumber('Mesh.MeshSizeMax',h);gmsh.model.mesh.generate(2)
ids,p,_=gmsh.model.mesh.getNodes();p=np.array(p).reshape(-1,3)[:,:2];types,_,cells=gmsh.model.mesh.getElements(2);t=np.array(cells[list(types).index(2)]).reshape(-1,3);lookup=np.zeros(int(ids.max())+1,dtype=int);lookup[ids]=np.arange(len(ids));t=lookup[t];gmsh.finalize()
used,inv=np.unique(t,return_inverse=True);p=p[used];t=inv.reshape(-1,3);N=len(p);m=MeshTri(p.T,t.T);basis=Basis(m,ElementVector(ElementTriP1()))
def thickness(x,y):
 inside=contains_xy(core,x,y);out=np.zeros_like(x)
 for z in np.arange(.1,24,.2):
  layer=(z<1.2) or (7.6<z<8.8) or (15.2<z<16.4) or(z>22.8)
  mat=~inside if not layer else np.ones(x.shape,dtype=bool)
  for fix in [164,40]:
   access=access_profile(fix);guard=access.buffer(w)
   mat|=contains_xy(guard,y,np.full_like(y,z))
   void=contains_xy(access,y,np.full_like(y,z))&(x>3.6)
   bore=access_profile(fix,2.6,12+2.6*np.sqrt(2),0)
   void|=contains_xy(bore,y,np.full_like(y,z))&(x<=3.6)
   mat&=~void
  out+=.2*mat
 return out
E=1000.;nu=.35;mu=E/(2*(1+nu));lam=E*nu/(1-nu**2)
@BilinearForm
def form(u,v,z):return z.th*(2*mu*ddot(sym_grad(u),sym_grad(v))+lam*trace(sym_grad(u))*trace(sym_grad(v)))
coords=basis.global_coordinates();th=thickness(coords[0],coords[1]);K=asm(form,basis,th=th).tocsr();f=np.zeros(2*N)
edges=m.facets[:,m.boundary_facets()].T;ec=p[edges].mean(1);length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1);patches={}
H=58.86*50/np.sqrt((90+12.4)**2-50**2)
for x,s,label in [(90,-1,'rear_seat'),(190,1,'front_seat')]:
 theta=np.arctan2(ec[:,1],ec[:,0]-x);target=np.arctan2(-58.86,s*H);da=np.arctan2(np.sin(theta-target),np.cos(theta-target));mask=(abs(np.hypot(ec[:,0]-x,ec[:,1])-13)<.12)&(abs(da)<np.deg2rad(25));es=edges[mask];wt=length[mask];wt=wt/wt.sum()/2
 for j in range(2):
  for k,F in enumerate([s*H,-58.86]):np.add.at(f,2*es[:,j]+k,wt*F)
 patches[label]=np.unique(es)
wall=np.where(abs(p[:,0])<1e-6)[0];base=[]
for y in [164,40]:
 head=wall[abs(p[wall,1]-y)<6.5];shank=wall[abs(p[wall,1]-y)<2.6];base.extend(2*head);base.extend(2*shank+1)
active=wall.copy();u=np.zeros(2*N)
for it in range(30):
 fixed=np.union1d(base,2*active).astype(int);free=np.setdiff1d(np.arange(2*N),fixed);u[:]=0;u[free]=spsolve(K[free][:,free],f[free]);r=K@u-f;new=wall[(r[2*wall]-K.diagonal()[2*wall]*u[2*wall])>1e-7]
 if np.array_equal(new,active):break
 active=new
else:raise RuntimeError('contact not converged')
g=basis.interpolate(u).grad.mean(-1);eps=(g+g.transpose(1,0,2))/2;sig=2*mu*eps+lam*np.einsum('iie->e',eps)[None,None,:]*np.eye(2)[:,:,None];vm=np.sqrt(sig[0,0]**2-sig[0,0]*sig[1,1]+sig[1,1]**2+3*sig[0,1]**2)
res={'name':name,'nodes':N,'triangles':len(t),'E_reference_MPa':E,'nu':nu,'contact_iterations':it+1,'applied_force_N':f.reshape(-1,2).sum(0).tolist(),'reaction_N':r.reshape(-1,2).sum(0).tolist(),'relative_free_residual':float(np.linalg.norm(r[free])/np.linalg.norm(f[free])),'vm_max_MPa_not_allowable':float(vm.max()),'patches':{k:{'mean_displacement_mm_at_E1000':u.reshape(-1,2)[v].mean(0).tolist()} for k,v in patches.items()}}
np.savez_compressed(D/f'{name}-solution.npz',p=p,t=t,u=u.reshape(-1,2),vm=vm,thickness=th.mean(1));(D/f'{name}-results.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
