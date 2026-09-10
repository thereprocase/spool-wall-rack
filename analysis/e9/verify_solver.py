"""Known affine solution checks stiffness, stress recovery and strain energy."""
from pathlib import Path
import json,numpy as np
from skfem import MeshTet,Basis,ElementVector,ElementTetP1,asm
from skfem.models.elasticity import linear_elasticity
from scipy.sparse.linalg import spsolve
m=MeshTet.init_tensor(np.linspace(0,10,6),np.linspace(0,4,4),np.linspace(0,3,4));b=Basis(m,ElementVector(ElementTetP1()))
E=1000.;nu=.35;sigma=2.;mu=E/(2*(1+nu));la=E*nu/((1+nu)*(1-2*nu));K=asm(linear_elasticity(la,mu),b)
p=m.p.T;exact=np.column_stack([sigma/E*p[:,0],-nu*sigma/E*p[:,1],-nu*sigma/E*p[:,2]]).ravel();fixed=b.get_dofs().all();free=np.setdiff1d(np.arange(b.N),fixed);u=exact.copy();u[free]=spsolve(K[free][:,free],-K[free][:,fixed]@u[fixed]);g=b.interpolate(u).grad.mean(-1);eps=(g+g.transpose(1,0,2))/2;stress=2*mu*eps+la*np.einsum('iie->e',eps)[None,None,:]*np.eye(3)[:,:,None];target=np.zeros_like(stress);target[0,0]=sigma
out={'patch_displacement_error_mm':float(abs(u-exact).max()),'patch_stress_error_MPa':float(abs(stress-target).max()),'FE_energy_Nmm':float(.5*u@K@u),'analytic_energy_Nmm':sigma*sigma/(2*E)*120}
assert out['patch_stress_error_MPa']<1e-8
assert abs(out['FE_energy_Nmm']-out['analytic_energy_Nmm'])<1e-8
Path(__file__).with_name('solver-verification.json').write_text(json.dumps(out,indent=2))
print(out)
