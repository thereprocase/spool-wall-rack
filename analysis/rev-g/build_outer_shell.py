"""Rev G variable walls/skins/planes, cut from the unchanged E13 outer geometry.

Never use these sparse-core domains as printable geometry. The chamfer guards
shift each finished bevel plane inward by the selected XY wall thickness.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import cadquery as cq
from shapely.geometry import Polygon
D=Path(__file__).resolve().parent
SRC=D.parents[1]/'designs/closed-wall-e13'
sys.path.insert(0,str(SRC))
import build_step as b
from fastener_geometry import access_profile,x_prism,FIXINGS

def thickness(n):return .42+(n-1)*(.45-.2*(1-np.pi/4))

def build(n,skin=1.2,plane=1.2):
 lower_plane_start=float(np.floor((8.2-plane/2)/.2+.5+1e-9)*.2)
 p=b.read_polys('profile.svg')[0]
 if not Polygon(p).exterior.is_ccw:p=p[::-1]
 wall=thickness(n);inner=Polygon(p).buffer(-wall,quad_segs=8)
 assert inner.geom_type=='Polygon' and inner.is_valid
 body=cq.importers.importStep(str(SRC/'body-only.step')).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
 spec=json.loads((SRC/'finish-specification.json').read_text());slope=np.tan(np.deg2rad(spec['angle_above_bed_deg']))
 edges=spec['edges'];cutters=[]
 for e in edges:
  a=np.array(e['a']);c=np.array(e['b']);t=(c-a)/np.linalg.norm(c-a);normal=np.array([-t[1],t[0]])
  da=e['depth_start_mm']+wall;dc=e['depth_end_mm']+wall;outside=3.
  # Segment planes overlap by 0.02 mm, below the 0.02 mm mesh export tolerance.
  # At curved joins include the miter extension required for the inward offset.
  i=len(cutters);L=np.linalg.norm(c-a)
  prev=np.array(edges[(i-1)%len(edges)]['b'])-np.array(edges[(i-1)%len(edges)]['a']);prev/=np.linalg.norm(prev)
  nxt=np.array(edges[(i+1)%len(edges)]['b'])-np.array(edges[(i+1)%len(edges)]['a']);nxt/=np.linalg.norm(nxt)
  def extension(u,v,d):return min(10.,d*abs(np.linalg.det(np.column_stack([u,v])))/max(1e-6,1+u@v))+.02
  ea=extension(prev,t,da);ec=extension(t,nxt,dc)
  def V(s,z):return cq.Vector(*(a+s*t-outside*normal),z)
  wire=cq.Wire.makePolygon([V(-ea,(outside+da)*slope),V(L+ec,(outside+dc)*slope),V(L+ec,-outside),V(-ea,-outside)],close=True)
  travel=2*(outside+wall)
  cutters.append(cq.Solid.extrudeLinear(wire,[],cq.Vector(*(travel*normal),-travel*slope)))
 key=hashlib.sha256(json.dumps([p.tolist(),wall,spec,skin,plane],sort_keys=True).encode()).hexdigest()[:16]
 cache=D/'.work'/f'core-lower-v3-{n}w-{key}.brep';cache.parent.mkdir(exist_ok=True)
 if cache.exists():air=cq.importers.importBrep(str(cache)).val()
 else:
  air=b.prism(np.array(inner.exterior.coords)[:-1],skin,lower_plane_start-skin)
  for i in range(0,len(cutters),32):
   air=air.cut(*cutters[i:i+32])
   if not air.isValid():air=air.fix()
   assert air.isValid(),('Invalid analysis core',n,i)
   print('core chamfer',n,min(i+32,len(cutters)),len(cutters),flush=True)
  cq.exporters.export(air,str(cache))
 cores=[air,b.prism(np.array(inner.exterior.coords)[:-1],lower_plane_start+plane,24-2*(lower_plane_start+plane)),air.mirror('XY').translate((0,0,24))]
 keep=[x_prism(access_profile(y).buffer(wall,quad_segs=8),0,220) for y in FIXINGS]
 for k,air in enumerate(cores):
  air=air.cut(*keep)
  body=body.cut(air)
  assert body.isValid(),('Invalid body after core',n,k)
  print('body core',n,k,flush=True)
 assert len(body.Solids())==1
 cq.exporters.export(body,str(D/f'print-material-{n}w.brep'))
 coupon=body.intersect(cq.Solid.makeBox(10,24,24,cq.Vector(0,152,0)))
 cq.exporters.export(coupon,str(D/f'landing-{n}w.brep'))
 return {'walls':n,'skin_mm':skin,'plane_mm':plane,'effective_wall_mm':wall,'volume_mm3':body.Volume(),'valid':body.isValid(),'solid_count':len(body.Solids()),'source_STEP_sha256':hashlib.sha256((SRC/'body-only.step').read_bytes()).hexdigest(),'core_model':'Finished chamfer planes offset inward in XY; ideal tunnel surrounds; variable skins/internal planes; zero sparse-infill credit'}

if __name__=='__main__':
 for n in map(int,sys.argv[1:] or [8,10]):
  r=build(n);(D/f'geometry-{n}w.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
