"""Independent final delivered-CAD, full finger-profile and surface checks."""
from pathlib import Path
import json,math
import numpy as np
import cadquery as cq
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from shapely.geometry import Polygon,Point
import build_step as b
from continuous_chamfer import rots
from verify_sections import layer_polygons
from render_cpu import render
D=Path(__file__).resolve().parent

def load_mesh(path):
 r=vtk.vtkSTLReader();r.SetFileName(str(path));r.Update();return r.GetOutput()

def sector(c,rot,a0,a1,r=17.7):
 theta=np.radians(np.linspace(a0,a1,200))+rot
 return Polygon(np.vstack([c,np.array(c)+r*np.column_stack([np.cos(theta),np.sin(theta)]),c]))

body=cq.importers.importStep(str(D/'body-only.step')).val()
assembly=cq.importers.importStep(str(D/'bracket-with-modifier-helpers.step')).val()
assert body.isValid() and len(body.Solids())==1
assert assembly.isValid() and len(assembly.Solids())==3
record=json.loads((D/'build-verification.json').read_text())
record['valid_body']=body.isValid();record['body_validation']='Reimported delivered body-only.step'
(D/'build-verification.json').write_text(json.dumps(record,indent=2)+'\n')
meshes={rev:load_mesh(D.parent/f'closed-wall-{rev}'/'body-mounted.stl') for rev in ['e10','e11']}
rows=[]
for label,c,rot in zip(['inner','outer'],[[90,0],[190,12]],rots):
 for side,a0,a1 in [('left',150,195),('right',345,390)]:
  region=sector(c,rot,a0,a1)
  for z in [.1,.7,1.7,3.,12.,21.,22.3,23.3,23.9]:
   a=layer_polygons(meshes['e10'],z).intersection(region)
   q=layer_polygons(meshes['e11'],z).intersection(region)
   # Distances allow the documented 0.02 mm STL chord tolerance.
   missing=a.difference(q.buffer(.025)).area
   added=q.difference(a.buffer(.025)).area
   rows.append({'seat':label,'finger':side,'print_z_mm':z,'reference_area_mm2':a.area,'E11_area_mm2':q.area,'missing_beyond_0p025mm_mm2':missing,'added_beyond_0p025mm_mm2':added})
   assert missing<.001 and added<.001,rows[-1]
report={'delivered_body_valid':True,'delivered_assembly_valid':True,'finger_comparisons':rows,'comparison_tolerance_mm':.025,'scope':'Complete flexible-finger sectors at nine depths through the delivered STL, compared with E10. Rigid bearing/chamfer sectors are outside this preservation mask. Physical insertion and fatigue are untested.'}
(D/'final-finish-verification.json').write_text(json.dumps(report,indent=2)+'\n')
for label,bounds in [('inner',[56,124,-30,24,-1,25]),('outer',[159,213,-22,38,-1,25])]:
 # Crop the camera framing, not triangles: preserve every visible CAD surface.
 m=meshes['e11']
 pts=vtk_to_numpy(m.GetPoints().GetData());idx=vtk_to_numpy(m.GetPolys().GetConnectivityArray()).reshape(-1,3)
 v=pts[idx].astype(float)[:,:,[0,2,1]];v[:,:,1]*=-1
 focus=np.array([[x,-z,y] for x in bounds[:2] for y in bounds[2:4] for z in bounds[4:]])
 for face,view in [('front',(25,-57)),('reverse',(25,57))]:
  render(f'finish-{label}-{face}.png',[(v,(.23,.52,.54))],f'E11 / {label.upper()} RETAINER / {face.upper()} FACE','Actual finished CAD crop · preserved finger profile · smooth bevel runouts',view=view,lim=focus)
print('Delivered solids and complete finger sectors pass; four finish details rendered',flush=True)
