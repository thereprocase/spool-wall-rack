"""Build E13 solid CAD body and aligned modifier slabs; no infill modeled.
Run after generating profile.svg with bracket.scad.
"""
from pathlib import Path
import json,re,xml.etree.ElementTree as ET
import numpy as np
import cadquery as cq
from matplotlib.path import Path as MPath
D=Path(__file__).resolve().parent
WIDTH=24.0; CHAMFER=2.0; FACE=1.2; TOL=.005

def rdp(p,tol):
 if len(p)<3:return p
 ab=p[-1]-p[0];den=ab@ab
 if den<1e-18:dist=np.linalg.norm(p-p[0],axis=1)
 else:
  t=np.clip(((p-p[0])@ab)/den,0,1);dist=np.linalg.norm(p-(p[0]+t[:,None]*ab),axis=1)
 i=int(dist.argmax())
 if dist[i]<=tol:return p[[0,-1]]
 return np.concatenate([rdp(p[:i+1],tol)[:-1],rdp(p[i:],tol)])

def read_polys(name):
 root=ET.parse(D/name).getroot();out=[]
 for e in root.findall('{http://www.w3.org/2000/svg}path'):
  for s in e.attrib['d'].split('M')[1:]:
   p=np.array([list(map(float,x)) for x in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)])*[1,-1]
   p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7]]
   k=int(np.linalg.norm(p-p[0],axis=1).argmax())
   p=np.concatenate([rdp(p[:k+1],TOL)[:-1],rdp(np.vstack([p[k:],p[:1]]),TOL)[:-1]])
   out.append(p)
 return out

def prism(p,z,h):
 w=cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in p],close=True)
 return cq.Solid.extrudeLinear(w,[],cq.Vector(0,0,h))

if __name__=='__main__':
 p=read_polys('profile.svg')[0];boundary=MPath(p)
 print('Profile vertices:',len(p),flush=True)
 body=prism(p,0,WIDTH)
 from continuous_chamfer import finish
 outer,finish_spec=finish(body,p)
 (D/'finish-specification.json').write_text(json.dumps(finish_spec,indent=2))
 assert outer.isValid(),'Invalid chamfered exterior'
 from fastener_geometry import FIXINGS, LAND, access_profile, x_prism
 result=outer
 for y in FIXINGS:
  result=result.cut(x_prism(access_profile(y),LAND,220))
  # Small screw clearance also has a 45-degree upper relief for side printing.
  bore=access_profile(y,radius=2.6,roof_z=12+2.6*2**.5,round_top=0)
  result=result.cut(x_prism(bore,-1,LAND+1.01))
 print('Fastener access complete',flush=True)
 assert result.isValid() and len(result.Solids())==1
 printed=result.rotate((0,0,0),(0,0,1),180).translate((250,182,0))
 cq.exporters.export(result.copy(),str(D/'body-mounted.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(printed.copy(),str(D/'body-only.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(printed,str(D/'body-only.step'))
 bb=printed.BoundingBox()
 assembly=cq.Assembly(name='E13_BODY_AND_MODIFIER_HELPERS')
 assembly.add(printed,name='MAIN_BODY_SET_WALLS_AND_INFILL',color=cq.Color(.20,.49,.51))
 helpers=[]
 for index,z in enumerate([7.6,15.2],1):
  helper=cq.Solid.makeBox(bb.xlen+4,bb.ylen+4,1.2,cq.Vector(bb.xmin-2,bb.ymin-2,z))
  name=f'MODIFIER_{index}_100_PERCENT_INFILL_Z_{z:.1f}_TO_{z+1.2:.1f}_MM'
  assembly.add(helper,name=name,color=cq.Color(.88,.60,.19))
  cq.exporters.export(helper,str(D/f'helper-{index}.stl'),tolerance=.02,angularTolerance=.1)
  helpers.append({'name':name,'z_min_mm':z,'z_max_mm':z+1.2,'thickness_mm':1.2,
                  'xy_bounds_mm':[bb.xmin-2,bb.ymin-2,bb.xmax+2,bb.ymax+2]})
 assembly.save(str(D/'bracket-with-modifier-helpers.step'))
 delivered=cq.importers.importStep(str(D/'body-only.step')).val()
 assert delivered.isValid() and len(delivered.Solids())==1
 # Body solids are an envelope for slicing, not a fully solid print instruction.
 (D/'build-verification.json').write_text(json.dumps({
  'revision':'E13','valid_body':delivered.isValid(),'body_validation':'Reimported delivered body-only.step', 'body_solid_count':len(delivered.Solids()),
  'assembly_body_count':3,'body_CAD_envelope_volume_cm3':result.Volume()/1000,
  'body_print_bounds_mm':[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],
  'helpers':helpers,'default_layer_mm':.2,'default_outer_top_bottom_mm':1.2,
  'front_rail_lift_mm':12,'broad_face_chamfer_inset_mm':2,'broad_face_chamfer_angle_above_bed_deg':50,
  'broad_face_chamfer_rise_mm':float(2*np.tan(np.deg2rad(50))),
  'body_angular_fillet_mm':2,'rear_rigid_shoulder_blend_mm':6,'rear_underside_added_depth_mm':11,
  'default_body_infill_percent':15,'helper_infill_percent':100,
  'body_wall_count':'User-selected; confirm actual sliced wall thickness.',
  'fastener_geometry':'Retained from E7; no modeled infill cells or large internal void bands.',
  'limitations':['STEP carries geometry and component names, not slicer modifier settings.',
  'Import as one object with aligned parts; change both helper parts to modifiers before slicing.',
  '100% modifier infill sets internal plates; the slicer generates supporting sparse infill.',
  'CAD envelope volume is not printed plastic volume or print mass.',
  'Previous hollow-CAD section properties do not rate a user-selected slicing setup.']},indent=2))
 print('E13 body and modifier STEP exported',flush=True)
