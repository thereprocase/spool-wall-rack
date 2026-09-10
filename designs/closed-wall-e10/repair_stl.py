"""Close only tiny STL tessellation pinholes; the STEP remains unchanged.

OpenCASCADE can omit near-degenerate triangles at intersecting chamfer facets.
Require all boundary loops to fit within a 0.1 mm box, add only their missing
triangles, then require a closed manifold when the written STL is re-read.
"""
from pathlib import Path
import json,numpy as np,vtk
from vtk.util.numpy_support import vtk_to_numpy
D=Path(__file__).resolve().parent

def read(path):
 r=vtk.vtkSTLReader();r.SetFileName(str(path));r.Update();return r.GetOutput()
def boundary(m):
 p=vtk_to_numpy(m.GetPoints().GetData());f=vtk_to_numpy(m.GetPolys().GetConnectivityArray()).reshape(-1,3)
 e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);e,c=np.unique(e,axis=0,return_counts=True)
 assert c.max()<=2,'Non-manifold STL intersection'
 return p,f,e[c==1]
def repair(path):
 m=read(path);p,f,e=boundary(m);groups=[];todo=set(map(int,e.ravel()));adj={i:set() for i in todo}
 for a,b in e:adj[int(a)].add(int(b));adj[int(b)].add(int(a))
 while todo:
  found={todo.pop()};stack=list(found)
  while stack:
   for j in adj[stack.pop()]-found:found.add(j);todo.discard(j);stack.append(j)
  assert all(len(adj[j])==2 for j in found),'Open or branching boundary'
  extent=float(np.linalg.norm(np.ptp(p[list(found)],axis=0)));assert extent<.1,extent
  groups.append({'vertices':len(found),'bounding_diagonal_mm':extent})
 if groups:
  fill=vtk.vtkFillHolesFilter();fill.SetInputData(m);fill.SetHoleSize(.1);fill.Update()
  normals=vtk.vtkPolyDataNormals();normals.SetInputData(fill.GetOutput());normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.SplittingOff();normals.Update()
  writer=vtk.vtkSTLWriter();writer.SetFileName(str(path));writer.SetFileTypeToBinary();writer.SetInputData(normals.GetOutput());assert writer.Write()==1
 _,g,bad=boundary(read(path));assert len(bad)==0,(path,len(bad))
 return {'file':path.name,'tiny_loops_closed':groups,'triangles_added':len(g)-len(f),'closed_after_roundtrip':True,'STEP_modified':False}
if __name__=='__main__':
 rows=[repair(D/n) for n in ['body-only.stl','body-mounted.stl']]
 (D/'stl-tessellation-check.json').write_text(json.dumps(rows,indent=2));print(rows)
