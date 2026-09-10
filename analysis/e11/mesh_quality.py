"""Remove numerically zero-volume tetrahedra; retain an explicit geometry audit.

Gmsh can emit coplanar/collinear cells at CAD surface intersections. Such cells
have no finite-element volume and must not enter a stiffness assembly. This is
not a filter for inconvenient stresses or merely low-quality finite cells.
"""
import numpy as np

def clean(p,t):
 v=p[t];m=np.stack([v[:,i]-v[:,0] for i in (1,2,3)],axis=2)
 det=np.abs(np.linalg.det(m));edge=np.max(np.linalg.norm(v[:,:,None,:]-v[:,None,:,:],axis=3),axis=(1,2))
 ratio=det/np.maximum(edge**3,np.finfo(float).tiny)
 bad=ratio<1e-12
 audit={'input_tetrahedra':len(t),'removed_numerically_degenerate_cells':int(bad.sum()),'normalized_determinant_floor':1e-12,'removed_absolute_volume_mm3':float(det[bad].sum()/6),'total_absolute_volume_mm3':float(det.sum()/6),'minimum_retained_normalized_determinant':float(ratio[~bad].min())}
 assert audit['removed_absolute_volume_mm3'] < 1e-8, 'Non-negligible material removal: remesh instead'
 t=t[~bad];used,inv=np.unique(t,return_inverse=True)
 return p[used],inv.reshape(-1,4),audit
