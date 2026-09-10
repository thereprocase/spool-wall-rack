"""Finish E6 broad-face edges and preserve solid material behind the chamfers.
Run after generating profile.svg and cavity-profile.svg with bracket.scad.
"""
from pathlib import Path
import json,re,xml.etree.ElementTree as ET
import numpy as np
import cadquery as cq
from matplotlib.path import Path as MPath
D=Path(__file__).resolve().parent
WIDTH=24.0; CHAMFER=3.0; FACE=1.2; TOL=.005

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
 Fade controls [0,0,0,3,3,3] give zero slope/curvature at either end.
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
 p=read_polys('profile.svg')[0];hp=read_polys('cavity-profile.svg');boundary=MPath(p)
 print('Profile vertices:',len(p),'cavity vertices:',[len(q) for q in hp],flush=True)
 body=prism(p,0,WIDTH)
 pairs=[];edge_specs=[]
 for a,b in zip(p,np.roll(p,-1,axis=0)):
  L=np.linalg.norm(b-a)
  if L<14:continue
  da=min(np.linalg.norm(a-[x,0]) for x in [90,190]);db=min(np.linalg.norm(b-[x,0]) for x in [90,190])
  # Small nearby faces and both retainer assemblies keep their full section.
  if max(da,db)<55 and L<50:continue
  # Fade into the R2 upper facet junction too, avoiding a hard bevel end cap.
  fs=bool(da<55 or np.linalg.norm(a-[24,114])<1)
  fe=bool(db<55 or np.linalg.norm(b-[24,114])<1)
  pairs.append((a,b));edge_specs.append((a,b,fs,fe))
 print('Selected outline edges:',len(edge_specs),flush=True)
 outer=body;guards=[]
 # The 1.8 mm buffer exceeds 1.2*sqrt(2+max(depth_gradient)^2).
 guard_extra=1.8
 for i,(a,b,fs,fe) in enumerate(edge_specs):
  for top in [False,True]:
   outer=outer.cut(smooth_cutter(a,b,fs,fe,top=top))
   guards.append(smooth_cutter(a,b,fs,fe,extra=guard_extra,top=top))
  print('Finished edge pair',i+1,flush=True)
 assert outer.isValid(),'Invalid chamfered exterior'
 guard_distance=CHAMFER+guard_extra
 sleeves=[cq.Solid.makeCylinder(5.15,75,cq.Vector(-1,y,12),cq.Vector(1,0,0)) for y in [164,12]]
 cavities=[]
 for i,z in enumerate([1.2,8.8,16.4]):
  air=prism(hp[0],z,6.4)
  for q in hp[1:]:air=air.cut(prism(q,z,6.4))
  if i!=1:
   relevant=guards[0::2] if i==0 else guards[1::2]
   for g in relevant:air=air.cut(g)
  for sl in sleeves:air=air.cut(sl)
  cavities.append(air)
  print('Prepared cavity',i+1,flush=True)
 result=outer
 for i,air in enumerate(cavities):
  result=result.cut(air);print('Cut cavity',i+1,flush=True)
 for y in [164,12]:result=result.cut(cq.Solid.makeCylinder(2.75,75,cq.Vector(-1,y,12),cq.Vector(1,0,0)))
 assert result.isValid(),'Invalid final solid'
 assert len(result.Solids())==1,'Disconnected bracket'
 cq.exporters.export(result,str(D/'bracket.step'))
 # Match the existing single-P1S orientation.
 printed=result.rotate((0,0,0),(0,0,1),180).translate((250,182,0))
 cq.exporters.export(printed,str(D/'bracket.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(result,str(D/'mounted.stl'),tolerance=.02,angularTolerance=.08)
 record={'revision':'E6','chamfer_mm':CHAMFER,'body_corner_fillet_mm':2,'width_mm':WIDTH,'face_and_internal_plate_mm':FACE,
 'profile_simplification_tolerance_mm':TOL,'selected_chamfer_edges':2*len(edge_specs),'fade_run_mm':20,'fade_curve':'quintic Bezier; C2 at zero/full depth','fade_endpoints':[[fs,fe] for a,b,fs,fe in edge_specs],'paired_outline_edges':[[a.tolist(),b.tolist()] for a,b in pairs],
 'bevel_rim_keepout_distance_mm':guard_distance,'minimum_design_ligament_mm':FACE,'rim_guard_extra_mm':guard_extra,
 'valid_brep':result.isValid(),'solid_count':len(result.Solids()),'material_volume_cm3':result.Volume()/1000,
 'limitations':['No slicing, print trial, snap-force test, structural load or creep rating.','Thin snap fingers and small functional edges are excluded from the 3 mm chamfer.']}
 (D/'finish-verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)
