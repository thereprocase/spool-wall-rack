"""Build E9 solid CAD body and aligned modifier slabs; no infill modeled.
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

def smooth_cutter(a,b,fade_start,fade_end,extra=0,top=False):
 """Exact quintic fade: z + inward_distance = depth(s).
 Fade controls [0,0,0,2,2,2] give zero slope/curvature at either end.
 """
 t=(b-a)/np.linalg.norm(b-a);n=np.array([-t[1],t[0]])
 if not boundary.contains_point((a+b)/2+n*.1):n=-n
 L=np.linalg.norm(b-a);run=min(20.,(L/2-.01) if fade_start and fade_end else L-.01);outside=8.
 s0=0. if fade_start else -6.;s1=L if fade_end else L+6.
 def pt(s,q):
  xy=a+t*s-n*outside
  return cq.Vector(xy[0],xy[1],outside+q+extra)
 es=[]
 if fade_start:
  es.append(cq.Edge.makeBezier([pt(i*run/5,q) for i,q in enumerate([0,0,0,CHAMFER,CHAMFER,CHAMFER])]))
 mid0=run if fade_start else s0;mid1=L-run if fade_end else s1
 es.append(cq.Edge.makeLine(pt(mid0,CHAMFER),pt(mid1,CHAMFER)))
 if fade_end:
  es.append(cq.Edge.makeBezier([pt(L-run+i*run/5,q) for i,q in enumerate([CHAMFER,CHAMFER,CHAMFER,0,0,0])]))
 lo1=pt(s1,-2*outside-extra);lo0=pt(s0,-2*outside-extra)
 es.extend([cq.Edge.makeLine(es[-1].endPoint(),lo1),cq.Edge.makeLine(lo1,lo0),cq.Edge.makeLine(lo0,es[0].startPoint())])
 w=cq.Wire.assembleEdges(es)
 cutter=cq.Solid.extrudeLinear(w,[],cq.Vector(*(n*2*outside),-2*outside))
 if top:cutter=cutter.mirror('XY').translate((0,0,WIDTH))
 return cutter

if __name__=='__main__':
 p=read_polys('profile.svg')[0];boundary=MPath(p)
 print('Profile vertices:',len(p),flush=True)
 body=prism(p,0,WIDTH)
 pairs=[];edge_specs=[]
 for a,b in zip(p,np.roll(p,-1,axis=0)):
  L=np.linalg.norm(b-a)
  if L<14:continue
  da=min(np.linalg.norm(a-c) for c in [np.array([90,0]),np.array([190,12])]);db=min(np.linalg.norm(b-c) for c in [np.array([90,0]),np.array([190,12])])
  # Small nearby faces and both retainer assemblies keep their full section.
  if max(da,db)<55 and L<50:continue
  # Fade into the R2 upper facet junction too, avoiding a hard bevel end cap.
  fs=True
  fe=True
  pairs.append((a,b));edge_specs.append((a,b,fs,fe))
 print('Selected outline edges:',len(edge_specs),flush=True)
 (D/'finish-specification.json').write_text(json.dumps({'chamfer_mm':CHAMFER,'width_mm':WIDTH,'edges':[{'a':a.tolist(),'b':b.tolist(),'fade_start':fs,'fade_end':fe} for a,b,fs,fe in edge_specs]},indent=2))
 outer=body
 for i,(a,b,fs,fe) in enumerate(edge_specs):
  for top in [False,True]:
   outer=outer.cut(smooth_cutter(a,b,fs,fe,top=top))

  print('Finished edge pair',i+1,flush=True)
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
 cq.exporters.export(result,str(D/'body-mounted.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(printed,str(D/'body-only.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(printed,str(D/'body-only.step'))
 bb=printed.BoundingBox()
 assembly=cq.Assembly(name='E9_BODY_AND_MODIFIER_HELPERS')
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
 # Body solids are an envelope for slicing, not a fully solid print instruction.
 (D/'build-verification.json').write_text(json.dumps({
  'revision':'E9','valid_body':result.isValid(),'body_solid_count':len(result.Solids()),
  'assembly_body_count':3,'body_CAD_envelope_volume_cm3':result.Volume()/1000,
  'body_print_bounds_mm':[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],
  'helpers':helpers,'default_layer_mm':.2,'default_outer_top_bottom_mm':1.2,
  'front_rail_lift_mm':12,'broad_face_chamfer_mm':2,'body_angular_fillet_mm':2,
  'default_body_infill_percent':15,'helper_infill_percent':100,
  'body_wall_count':'User-selected; confirm actual sliced wall thickness.',
  'fastener_geometry':'Retained from E7; no modeled infill cells or large internal void bands.',
  'limitations':['STEP carries geometry and component names, not slicer modifier settings.',
  'Import as one object with aligned parts; change both helper parts to modifiers before slicing.',
  '100% modifier infill sets internal plates; the slicer generates supporting sparse infill.',
  'CAD envelope volume is not printed plastic volume or print mass.',
  'Previous hollow-CAD section properties do not rate a user-selected slicing setup.']},indent=2))
 print('E9 body and modifier STEP exported',flush=True)
