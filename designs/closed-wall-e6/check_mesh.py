from pathlib import Path
import json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
D=Path(__file__).resolve().parent
report={}
for name in ['bracket.stl','snap-coupon-8mm.stl']:
 r=vtk.vtkSTLReader();r.SetFileName(str(D/name));r.Update();p=r.GetOutput()
 v=vtk_to_numpy(p.GetPoints().GetData()).astype(float);f=vtk_to_numpy(p.GetPolys().GetData()).reshape(-1,4)[:,1:]
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
 bad=int((counts!=2).sum());assert bad==0,'Unclosed or nonmanifold mesh edges'
 if name=='bracket.stl':assert abs(v[:,0].min()-43.275)<.02,'STL does not match the new profile envelope'
 report[name]={'triangles':len(f),'edges_with_incidence_not_two':bad,'bounds_mm':list(p.GetBounds())}
(D/'mesh-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
