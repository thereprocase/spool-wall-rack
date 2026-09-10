from pathlib import Path
import re,json,zipfile,xml.etree.ElementTree as ET
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from scipy.spatial import cKDTree
D=Path(__file__).resolve().parent.parent

def mesh(path):
 r=vtk.vtkSTLReader();r.SetFileName(str(path));r.Update();return r.GetOutput()
p=mesh(D/'bracket.stl');v=vtk_to_numpy(p.GetPoints().GetData()).astype(float)
f=vtk_to_numpy(p.GetPolys().GetData()).reshape(-1,4)[:,1:]
e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);uniq,counts=np.unique(np.sort(e,axis=1),axis=0,return_counts=True)
volume=np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6
# Original source coordinates, undo the bed rotation.
ov=v.copy();ov[:,0]=250-v[:,0];ov[:,1]=156-v[:,1]
# Probe the CAD at the center of every expected 0.2 mm layer via mesh/plane intersection.
def section(z):
 plane=vtk.vtkPlane();plane.SetOrigin(0,0,z);plane.SetNormal(0,0,1)
 c=vtk.vtkCutter();c.SetInputData(p);c.SetCutFunction(plane);c.Update()
 strip=vtk.vtkStripper();strip.SetInputConnection(c.GetOutputPort());strip.JoinContiguousSegmentsOn();strip.Update()
 out=strip.GetOutput();pts=vtk_to_numpy(out.GetPoints().GetData());lines=vtk_to_numpy(out.GetLines().GetData())
 areas=[];i=0
 while i<len(lines):
  n=lines[i];q=pts[lines[i+1:i+1+n],:2];i+=n+1
  areas.append(float(abs(np.cross(q,np.roll(q,-1,axis=0)).sum()/2)))
 return {'z':round(z,2),'loops':len(areas),'areas_mm2':sorted(areas,reverse=True)}
sections=[section(z) for z in np.arange(.1,24,.2)]
# STL versus 3MF vertices, independently parse 3MF package.
with zipfile.ZipFile(D/'bracket.3mf') as z:
 root=ET.fromstring(z.read('3D/3dmodel.model'))
 ns={'m':root.tag.split('}')[0][1:]}
 mv=np.array([[float(e.attrib[k]) for k in ['x','y','z']] for e in root.findall('.//m:vertex',ns)])
 mf=np.array([[int(e.attrib[k]) for k in ['v1','v2','v3']] for e in root.findall('.//m:triangle',ns)])
err=max(cKDTree(v).query(mv)[0].max(),cKDTree(mv).query(v)[0].max())
report={'mesh_vertices':len(v),'mesh_triangles':len(f),'edges_with_incidence_not_two':int(np.count_nonzero(counts!=2)),
 'signed_solid_volume_cm3':float(volume/1000),'bbox_mm':[v.min(0).tolist(),v.max(0).tolist()],
 'stl_3mf_vertex_set_max_difference_mm':float(err),'3mf_triangles':len(mf),
 'sections':sections}
if (D/'audit/rebuilt.stl').exists():
 q=mesh(D/'audit/rebuilt.stl');qv=vtk_to_numpy(q.GetPoints().GetData())
 report['rebuilt_vertex_set_max_difference_mm']=float(max(cKDTree(v).query(qv)[0].max(),cKDTree(qv).query(v)[0].max()))
(D/'audit/mesh-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:val for k,val in report.items() if k!='sections'},indent=2))
print('Representative sections:')
for i in [0,6,37,38,43,44,75,76,81,82,113,114,119]:print(sections[i])
