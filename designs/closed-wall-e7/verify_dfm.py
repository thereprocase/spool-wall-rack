"""Verify actual final solid access, clamping lands, mesh closure and small coupons."""
from pathlib import Path
import json,math
import cadquery as cq
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from dfm_geometry import FIXINGS,LAND
D=Path(__file__).resolve().parent
if not (D/'bracket.step').exists():
 import zipfile
 with zipfile.ZipFile(D/'bracket-step.zip') as archive:
  (D/'bracket.step').write_bytes(archive.read('bracket.step'))
shape=cq.importers.importStep(str(D/'bracket.step')).val()
assert shape.isValid() and len(shape.Solids())==1

def cylinder(r,x,length,y):
 return cq.Solid.makeCylinder(r,length,cq.Vector(x,y,12),cq.Vector(1,0,0))

def overlap(a):
 common=shape.intersect(a)
 return sum(s.Volume() for s in common.Solids())

report={'valid_brep':True,'solid_count':1,'fasteners':[]}
for y in FIXINGS:
 tool=cylinder(7.9,LAND+.01,215,y)
 washer=cylinder(6.5,LAND+.01,1.2,y).cut(cylinder(2.75,LAND,1.3,y))
 land=cylinder(6.5,.1,LAND-.2,y).cut(cylinder(2.75,0,LAND,y))
 bore=cylinder(2.5,-.1,LAND+.2,y)
 rec={'axis_y_mm':y,'tool_check_diameter_mm':15.8,'tool_collision_mm3':overlap(tool),
      'washer_OD_mm':13,'washer_ID_mm':5.5,'washer_collision_mm3':overlap(washer),
      'clamping_land_mm':LAND,'washer_land_supported_fraction':overlap(land)/land.Volume(),
      'M5_nominal_shank_collision_mm3':overlap(bore)}
 assert rec['tool_collision_mm3']<1e-5
 assert rec['washer_collision_mm3']<1e-5
 assert rec['M5_nominal_shank_collision_mm3']<1e-5
 assert rec['washer_land_supported_fraction']>.95
 report['fasteners'].append(rec)
 print('Access verified',rec,flush=True)
# Extract actual upper fixing as a small print-fit coupon; retain print orientation.
fixing=shape.intersect(cq.Solid.makeBox(26,24,24,cq.Vector(0,152,0)))
assert fixing.isValid() and len(fixing.Solids())==1
fixing=fixing.translate((0,-152,0))
cq.exporters.export(fixing,str(D/'fastener-coupon.stl'),tolerance=.02,angularTolerance=.1)
# Small three-band roof coupon repeats 10 mm cells, R2 corners and 1.2 dividers.
block=cq.Solid.makeBox(36,36,24)
voids=[]
for z in [1.2,8.8,16.4]:
 for x in [1.8,13,24.2]:
  for y in [1.8,13,24.2]:
   w=cq.Workplane('XY').workplane(offset=z).center(x+5,y+5).rect(10,10).extrude(6.4).edges('|Z').fillet(2).val()
   voids.append(w)
block=block.cut(cq.Compound.makeCompound(voids))
assert block.isValid() and len(block.Solids())==1
cq.exporters.export(block,str(D/'bridge-coupon.stl'),tolerance=.03,angularTolerance=.1)
report['coupons']={'fastener_crop_envelope_mm':[26,24,24],'bridge_envelope_mm':[36,36,24],
                   'bridge_cavity_roof_start_z_mm':[7.6,15.2,22.8]}
report['meshes']={}
for name in ['bracket.stl','fastener-coupon.stl','bridge-coupon.stl']:
 r=vtk.vtkSTLReader();r.SetFileName(str(D/name));r.Update();mesh=r.GetOutput()
 f=vtk_to_numpy(mesh.GetPolys().GetConnectivityArray()).reshape(-1,3)
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
 _,counts=np.unique(edges,axis=0,return_counts=True)
 bad=int((counts!=2).sum());assert bad==0,(name,bad)
 report['meshes'][name]={'triangles':len(f),'edges_with_incidence_not_two':bad,'bounds_mm':list(mesh.GetBounds())}
report['limitations']=['Geometric clearance uses ideal dimensions; printed M5 clearance requires coupon confirmation.',
 'Washer landing has a small upper screw-hole roof relief; actual supported fraction is reported.',
 'Tool check is a straight 15.8 mm cylinder, not a drill-body or arbitrary angled-driver envelope.',
 'Install fasteners before loading spools. Rods do not intersect either proposed driver axis.',
 'STL closure and geometric bridge limits do not verify sliced paths, print quality or load capacity.']
(D/'dfm-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
