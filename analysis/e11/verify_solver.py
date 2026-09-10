"""Independent affine and cantilever checks for the reduced plane-stress law."""
from pathlib import Path
import json
import numpy as np
from scipy.sparse.linalg import spsolve
from skfem import MeshTri,Basis,ElementVector,ElementTriP1,BilinearForm,asm
from skfem.helpers import ddot,sym_grad,trace
E=1000.;nu=.35;thickness=2.
mu=E/(2*(1+nu));lam=E*nu/(1-nu**2)
@BilinearForm
def stiffness(u,v,w):
 return thickness*(2*mu*ddot(sym_grad(u),sym_grad(v))+lam*trace(sym_grad(u))*trace(sym_grad(v)))
def model(length,height,nx,ny):
 mesh=MeshTri.init_tensor(np.linspace(0,length,nx+1),np.linspace(-height/2,height/2,ny+1))
 basis=Basis(mesh,ElementVector(ElementTriP1()))
 return mesh,basis,asm(stiffness,basis).tocsr()
m,b,K=model(10,4,12,6);p=m.p.T;sigma=2.
exact=np.column_stack([sigma/E*p[:,0],-nu*sigma/E*p[:,1]]).ravel()
fixed=b.get_dofs().all();free=np.setdiff1d(np.arange(b.N),fixed)
u=exact.copy();u[free]=spsolve(K[free][:,free],-K[free][:,fixed]@u[fixed])
g=b.interpolate(u).grad.mean(-1);eps=(g+g.transpose(1,0,2))/2
stress=2*mu*eps+lam*np.einsum('iie->e',eps)[None,None,:]*np.eye(2)[:,:,None]
target=np.zeros_like(stress);target[0,0]=sigma
out={'model':'Plane stress, constant 2 mm thickness','patch_displacement_error_mm':float(abs(u-exact).max()),'patch_stress_error_MPa':float(abs(stress-target).max()),'FE_energy_Nmm':float(.5*u@K@u),'analytic_energy_Nmm':sigma*sigma/(2*E)*10*4*thickness}
assert out['patch_displacement_error_mm']<1e-10
assert out['patch_stress_error_MPa']<1e-8
assert abs(out['FE_energy_Nmm']-out['analytic_energy_Nmm'])<1e-8
# Slender 100 x 10 mm cantilever with a uniformly distributed 1 N end load.
# Timoshenko adds the small rectangular-section shear correction (k=5/6).
L=100.;H=10.;P=1.;I=thickness*H**3/12
beam=P*L**3/(3*E*I)+P*L/((5/6)*mu*thickness*H)
out['beam_analytic_bending_plus_shear_mm']=beam;out['beam_mesh_checks']=[]
for nx,ny in [(80,8),(320,32)]:
 m,b,K=model(L,H,nx,ny);p=m.p.T;f=np.zeros(b.N)
 edges=m.facets[:,m.boundary_facets()].T
 right=edges[np.all(np.isclose(p[edges,0],L),axis=1)]
 lengths=np.linalg.norm(p[right[:,1]]-p[right[:,0]],axis=1)
 for j in [0,1]:np.add.at(f,2*right[:,j]+1,-P*lengths/(2*H))
 left=np.where(np.isclose(p[:,0],0))[0];fixed=np.ravel(np.column_stack([2*left,2*left+1]))
 free=np.setdiff1d(np.arange(b.N),fixed);u=np.zeros(b.N);u[free]=spsolve(K[free][:,free],f[free])
 tip=-float(np.sum(u[2*right+1].mean(1)*lengths)/H)
 residual=float(np.linalg.norm((K@u-f)[free])/np.linalg.norm(f))
 row={'nx':nx,'ny':ny,'triangles':m.nelements,'tip_mean_mm':tip,'relative_error':abs(tip/beam-1),'relative_free_residual':residual}
 out['beam_mesh_checks'].append(row)
 assert residual<1e-7
assert out['beam_mesh_checks'][-1]['relative_error']<.03
assert out['beam_mesh_checks'][-1]['relative_error']<out['beam_mesh_checks'][0]['relative_error']
Path(__file__).with_name('solver-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
