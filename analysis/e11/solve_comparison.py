"""Comparative plane-stress screen with finished layer-integrated print material.

Reuses the repository's plane-stress constitutive law and unilateral wall
contact. Thickness is integrated from actual chamfered STL layer outlines,
with 8/10 contour walls, four solid plates, and zero sparse-infill credit.
Washer/shank restraints are projected onto the wall, as in the prior 2D model.
This cannot resolve through-width contact stresses, FFF orthotropy or creep.
"""
from pathlib import Path
import sys,json,re,xml.etree.ElementTree as ET,hashlib
import numpy as np
import gmsh,vtk
from shapely.geometry import Polygon
from shapely import contains_xy,to_wkb,from_wkb
from scipy.sparse.linalg import spsolve
from skfem import MeshTri,Basis,ElementVector,ElementTriP1,BilinearForm,asm
from skfem.helpers import ddot,sym_grad,trace
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'designs/closed-wall-e11'))
from verify_sections import layer_polygons
vtk.vtkLogger.SetStderrVerbosity(vtk.vtkLogger.VERBOSITY_OFF)
WORK=D/'.work';WORK.mkdir(exist_ok=True)

def material_layers(revision,walls):
 src=ROOT/f'designs/closed-wall-{revision}'
 stl=src/'body-mounted.stl';digest=hashlib.sha256(stl.read_bytes()).hexdigest()
 cache=WORK/f'{revision}-layer-outlines.json'
 old=json.loads(cache.read_text()) if cache.exists() else {}
 if old.get('stl_sha256')==digest:
  outlines=[from_wkb(bytes.fromhex(s)) for s in old['wkb_hex']]
 else:
  reader=vtk.vtkSTLReader();reader.SetFileName(str(stl));reader.Update();mesh=reader.GetOutput()
  tester=vtk.vtkSelectEnclosedPoints();tester.SetTolerance(1e-8);tester.Initialize(mesh)
  outlines=[layer_polygons(mesh,(k+.5)*.2,tester) for k in range(120)]
  tester.Complete()
  cache.write_text(json.dumps({'stl_sha256':digest,'wkb_hex':[to_wkb(p).hex() for p in outlines]}))
 width=.42+(walls-1)*(.45-.2*(1-np.pi/4));layers=[]
 for k,poly in enumerate(outlines):
  z=(k+.5)*.2
  plate=z<1.2 or 7.6<z<8.8 or 15.2<z<16.4 or z>22.8
  layers.append(poly if plate else poly.difference(poly.buffer(-width,quad_segs=12)))
 return layers,digest

def outline(revision):
 e=ET.parse(ROOT/f'designs/closed-wall-{revision}/profile.svg').getroot()
 s=e.find('{http://www.w3.org/2000/svg}path').attrib['d']
 p=Polygon([(float(x),-float(y)) for x,y in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)])
 assert p.is_valid
 return p.simplify(.005,preserve_topology=True)

def mesh_outline(poly,h):
 gmsh.initialize();gmsh.option.setNumber('General.Terminal',0);gmsh.model.add('rack')
 ids=[gmsh.model.geo.addPoint(x,y,0,h) for x,y in list(poly.exterior.coords)[:-1]]
 lines=[gmsh.model.geo.addLine(a,b) for a,b in zip(ids,ids[1:]+ids[:1])]
 loop=gmsh.model.geo.addCurveLoop(lines);gmsh.model.geo.addPlaneSurface([loop]);gmsh.model.geo.synchronize()
 gmsh.option.setNumber('Mesh.MeshSizeMin',.25);gmsh.option.setNumber('Mesh.MeshSizeMax',h);gmsh.model.mesh.generate(2)
 tags,p,_=gmsh.model.mesh.getNodes();p=np.array(p).reshape(-1,3)[:,:2]
 kinds,_,cells=gmsh.model.mesh.getElements(2);t=np.array(cells[list(kinds).index(2)]).reshape(-1,3)
 lookup=np.zeros(int(tags.max())+1,dtype=int);lookup[tags]=np.arange(len(tags));t=lookup[t];gmsh.finalize()
 used,inv=np.unique(t,return_inverse=True);return p[used],inv.reshape(-1,3)

def quantile(values,weights,q):
 order=np.argsort(values);return float(np.interp(q*weights.sum(),np.cumsum(weights[order]),values[order]))

def solve(revision,walls,h,load_case='full'):
 name=f'{revision}-{walls}w-h{h:g}-{load_case}';print('Start',name,flush=True)
 layers,digest=material_layers(revision,walls);p,t=mesh_outline(outline(revision),h);N=len(p)
 m=MeshTri(p.T,t.T);basis=Basis(m,ElementVector(ElementTriP1()));coords=basis.global_coordinates()
 th=np.zeros_like(coords[0])
 for layer in layers:th+=.2*contains_xy(layer,coords[0],coords[1])
 assert (th>0).all() and np.isfinite(th).all()
 E=1000.;nu=.35;mu=E/(2*(1+nu));lam=E*nu/(1-nu**2)
 @BilinearForm
 def form(u,v,z):return z.th*(2*mu*ddot(sym_grad(u),sym_grad(v))+lam*trace(sym_grad(u))*trace(sym_grad(v)))
 K=asm(form,basis,th=th).tocsr();f=np.zeros(2*N)
 edges=m.facets[:,m.boundary_facets()].T;ec=p[edges].mean(1);length=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1);patches={}
 S=np.hypot(100,12);q=np.sqrt((90+12.4)**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S
 aa=cx-90;bb=190-cx;den=aa*(cy-12)+bb*cy;H=117.72*aa*bb/den;Vr=117.72*bb*cy/den;Vf=117.72*aa*(cy-12)/den
 for x,sign,label in [(90,-1,'rear_seat'),(190,1,'front_seat')]:
  y=0 if x==90 else 12;V=Vr if x==90 else Vf
  theta=np.arctan2(ec[:,1]-y,ec[:,0]-x);target=np.arctan2(-V,sign*H)
  da=np.arctan2(np.sin(theta-target),np.cos(theta-target))
  mask=(abs(np.hypot(ec[:,0]-x,ec[:,1]-y)-13)<.12)&(abs(da)<np.deg2rad(25))
  es=edges[mask];wt=length[mask];assert len(es)>0
  force=np.array([sign*H,-V]) if load_case=='full' or x==190 else np.zeros(2)
  wt=wt/wt.sum()/2
  for j in range(2):
   for k,F in enumerate(force):np.add.at(f,2*es[:,j]+k,wt*F)
  patches[label]={'nodes':np.unique(es),'force_N':force.tolist()}
 wall=np.where(abs(p[:,0])<1e-6)[0];base=[]
 for y in [164,40]:
  head=wall[abs(p[wall,1]-y)<6.5];shank=wall[abs(p[wall,1]-y)<2.6]
  assert len(head) and len(shank)
  base.extend(2*head);base.extend(2*shank+1)
 active=wall.copy();u=np.zeros(2*N)
 for it in range(30):
  fixed=np.union1d(base,2*active).astype(int);free=np.setdiff1d(np.arange(2*N),fixed)
  u[:]=0;u[free]=spsolve(K[free][:,free],f[free]);reaction=K@u-f
  new=wall[(reaction[2*wall]-K.diagonal()[2*wall]*u[2*wall])>1e-7]
  if np.array_equal(new,active):break
  active=new
 else:raise RuntimeError('Contact did not converge')
 residual=float(np.linalg.norm(reaction[free])/np.linalg.norm(f[free]));assert residual<1e-6,residual
 force=f.reshape(-1,2).sum(0);R=reaction.reshape(-1,2).sum(0)
 moment=float((p[:,0]*f[1::2]-p[:,1]*f[0::2]).sum())
 r_moment=float((p[:,0]*reaction[1::2]-p[:,1]*reaction[0::2]).sum())
 assert np.linalg.norm(force+R)<1e-5 and abs(moment+r_moment)<1e-3
 gradient=basis.interpolate(u).grad.mean(-1);eps=(gradient+gradient.transpose(1,0,2))/2
 sig=2*mu*eps+lam*np.einsum('iie->e',eps)[None,None,:]*np.eye(2)[:,:,None]
 vm=np.sqrt(sig[0,0]**2-sig[0,0]*sig[1,1]+sig[1,1]**2+3*sig[0,1]**2)
 principal=np.linalg.eigvalsh(sig.transpose(2,0,1))[:,-1];volume=(basis.dx*th).sum(1);tc=p[t].mean(1)
 regions={'near_rear_seat_fixed_window':(tc[:,0]>75)&(tc[:,0]<110)&(tc[:,1]>-24)&(tc[:,1]<0),
  'reinforced_zone':(tc[:,0]>55)&(tc[:,0]<135)&(tc[:,1]<15),
  'forearm':(tc[:,0]>115)&(tc[:,0]<170),
  'knee':(tc[:,0]>30)&(tc[:,0]<75)&(tc[:,1]<40)}
 stats={}
 for key,mask in regions.items():
  indices=np.flatnonzero(mask);imax=indices[vm[mask].argmax()]
  stats[key]={'vm_volume_p99_MPa':quantile(vm[mask],volume[mask],.99),
   'raw_vm_max_MPa':float(vm[mask].max()),'max_principal_p99_MPa':quantile(principal[mask],volume[mask],.99),
   'peak_xy_mm':tc[imax].tolist()}
 res={'name':name,'revision':revision.upper(),'walls':walls,'mesh_h_mm':h,'load_case':load_case,
  'finished_STL_sha256':digest,'nodes':N,'triangles':len(t),'E_reference_MPa':E,'nu':nu,
  'relative_free_residual':residual,'contact_iterations':it+1,'applied_force_N':force.tolist(),
  'reaction_N':R.tolist(),'applied_moment_Nmm':moment,'reaction_moment_Nmm':r_moment,
  'raw_vm_max_MPa_not_allowable':float(vm.max()),'regions':stats,
  'patches':{key:{'force_N':a['force_N'],'mean_displacement_mm_at_E1000':u.reshape(-1,2)[a['nodes']].mean(0).tolist()} for key,a in patches.items()},
  'limitations':__doc__}
 np.savez_compressed(D/f'{name}-solution.npz',p=p,t=t,u=u.reshape(-1,2),vm=vm,principal=principal,stress=sig,volume=volume,thickness=th.mean(1))
 (D/f'{name}-results.json').write_text(json.dumps(res,indent=2)+'\n')
 print(name,'rear p99',stats['near_rear_seat_fixed_window']['vm_volume_p99_MPa'],'front uy',res['patches']['front_seat']['mean_displacement_mm_at_E1000'][1],'residual',residual,flush=True)
 return res

if __name__=='__main__':
 if len(sys.argv)>1:solve(sys.argv[1],int(sys.argv[2]),float(sys.argv[3]),sys.argv[4] if len(sys.argv)>4 else 'full')
 else:
  for revision in ['e10','e11']:
   for walls in [8,10]:
    for h in [2,1]:solve(revision,walls,h)
   solve(revision,8,1,'outer_only')
