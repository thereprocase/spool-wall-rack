"""STEP roundtrip and retained hardware clearances; no slicer or capacity claim."""
from pathlib import Path
import json
import cadquery as cq
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
D=Path(__file__).resolve().parent
assembly=cq.importers.importStep(str(D/'bracket-with-modifier-helpers.step')).val()
solids=assembly.Solids();assert len(solids)==3
assert all(s.isValid() for s in solids)
body=next(s for s in solids if s.BoundingBox().zlen>20)
helpers=sorted((s for s in solids if s.BoundingBox().zlen<2),key=lambda s:s.BoundingBox().zmin)
for h,z in zip(helpers,[7.6,15.2]):
 b=h.BoundingBox();bb=body.BoundingBox()
 assert abs(b.zmin-z)<1e-5 and abs(b.zlen-1.2)<1e-5
 assert b.xmin<bb.xmin and b.xmax>bb.xmax and b.ymin<bb.ymin and b.ymax>bb.ymax
 assert body.intersect(h).Volume()>0
# Return body alone to mounted coordinates for the inherited fixing checks.
mounted=body.translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
def cyl(r,x,length,y):return cq.Solid.makeCylinder(r,length,cq.Vector(x,y,12),cq.Vector(1,0,0))
def volume(a):return sum(s.Volume() for s in mounted.intersect(a).Solids())
rows=[]
for y in [164,40]:
 tool=volume(cyl(7.9,3.61,215,y))
 washer=volume(cyl(6.5,3.61,1.2,y).cut(cyl(2.75,3.6,1.3,y)))
 bore=volume(cyl(2.5,-.1,3.8,y))
 assert max(tool,washer,bore)<1e-5
 rows.append({'axis_y_mm':y,'driver_15p8_mm_collision_mm3':tool,'washer_13_mm_collision_mm3':washer,'M5_shank_collision_mm3':bore})
# A slice through each former air band now has no modeled cell lattice.
mesh_report={}
for name in ['body-only.stl','helper-1.stl','helper-2.stl']:
 r=vtk.vtkSTLReader();r.SetFileName(str(D/name));r.Update();m=r.GetOutput()
 f=vtk_to_numpy(m.GetPolys().GetConnectivityArray()).reshape(-1,3)
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
 _,counts=np.unique(edges,axis=0,return_counts=True)
 bad=int((counts!=2).sum());assert bad==0
 mesh_report[name]={'triangles':len(f),'nonmanifold_or_boundary_edges':bad}
report={'STEP_roundtrip_valid_solids':3,'one_body_plus_two_overlapping_helpers':True,
 'helpers_thickness_mm':1.2,'helpers_z_intervals_mm':[[7.6,8.8],[15.2,16.4]],
 'fasteners':rows,'meshes':mesh_report,
 'limitations':['Helper overlap is intentional; convert helpers to modifiers, never fuse or print them as extra parts.',
 'STEP does not encode infill or wall settings; user configures them in the slicer.',
 'Geometric envelope volume does not describe printed mass or strength.']}
(D/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
