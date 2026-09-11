"""Weld microscopic tessellation seams without changing the STEP.

The faceted chamfer exporter creates almost coincident vertices and collapsed
sliver faces. Weld within 0.00005 mm, discard only collapsed facets, and require
closed manifold edges, one connected component, bounded vertex movement and a
negligible signed-volume change. No hole filling or structural removal.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from scipy.spatial import cKDTree
D=Path(__file__).resolve().parent
TOLERANCE_MM=.00005

def read(path):
 r=vtk.vtkSTLReader();r.SetFileName(str(path));r.Update();return r.GetOutput()

def boundary(m):
 p=vtk_to_numpy(m.GetPoints().GetData());f=vtk_to_numpy(m.GetPolys().GetConnectivityArray()).reshape(-1,3)
 e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
 e,c=np.unique(e,axis=0,return_counts=True)
 assert c.max()<=2,'Non-manifold STL intersection'
 return p,f,e[c==1]

def signed_volume(p,f):
 v=p[f].astype(float)-p.mean(0)
 return float(np.einsum('ij,ij->i',v[:,0],np.cross(v[:,1],v[:,2])).sum()/6)

def repair(path):
 original_hash=hashlib.sha256(path.read_bytes()).hexdigest()
 m=read(path);p,f,edges=boundary(m)
 clean=vtk.vtkCleanPolyData();clean.SetInputData(m)
 clean.ToleranceIsAbsoluteOn();clean.SetAbsoluteTolerance(TOLERANCE_MM);clean.Update()
 tri=vtk.vtkTriangleFilter();tri.SetInputData(clean.GetOutput());tri.PassLinesOff();tri.PassVertsOff();tri.Update()
 out=tri.GetOutput();q,g,bad=boundary(out)
 assert len(bad)==0,(path.name,len(bad))
 max_move=float(cKDTree(q).query(p)[0].max())
 assert max_move<=TOLERANCE_MM*1.001,max_move
 delta=abs(signed_volume(p,f)-signed_volume(q,g))
 assert delta<.1 and delta/abs(signed_volume(q,g))<1e-6,delta
 connectivity=vtk.vtkPolyDataConnectivityFilter();connectivity.SetInputData(out)
 connectivity.SetExtractionModeToAllRegions();connectivity.Update()
 assert connectivity.GetNumberOfExtractedRegions()==1
 writer=vtk.vtkSTLWriter();writer.SetFileName(str(path));writer.SetFileTypeToBinary();writer.SetInputData(out)
 assert writer.Write()==1
 _,written,bad=boundary(read(path));assert len(bad)==0
 return {'file':path.name,'method':'weld near-coincident vertices and discard collapsed triangles; no hole filling',
  'weld_tolerance_mm':TOLERANCE_MM,'maximum_vertex_movement_mm':max_move,
  'input_boundary_edges':len(edges),'output_boundary_edges':0,'connected_components':1,
  'input_triangles':len(f),'output_triangles':len(written),'signed_volume_change_mm3':delta,
  'input_sha256':original_hash,'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
  'closed_after_roundtrip':True,'STEP_modified':False}

if __name__=='__main__':
 rows=[repair(D/n) for n in ['body-only.stl','body-mounted.stl']]
 (D/'stl-tessellation-check.json').write_text(json.dumps(rows,indent=2)+'\n')
 print([{k:v for k,v in r.items() if 'sha256' not in k} for r in rows])
