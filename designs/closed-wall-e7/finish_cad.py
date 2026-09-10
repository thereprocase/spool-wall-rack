"""Finish E7 broad-face edges and preserve solid material behind the chamfers.
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

def safe_cut(a,b):
 if a is None:return None
 aa=a.BoundingBox();bb=b.BoundingBox()
 if any(getattr(aa,k+'max')<getattr(bb,k+'min') or getattr(aa,k+'min')>getattr(bb,k+'max') for k in 'xyz'):return a
 common=a.intersect(b)
 if not common.Solids() or common.Volume()<1e-7:return a
 if common.Volume()>=a.Volume()-1e-6:return None
 return a.cut(b)

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
 # Compartmented true voids preserve the original full-profile solid plates.
 from shapely.geometry import Polygon, box, Point
 from shapely.ops import unary_union
 from shapely import to_geojson
 from dfm_geometry import cell_footprints, access_profile, x_prism, FIXINGS, LAND
 footprints=cell_footprints(hp)
 (D/'cavity-cells.geojson').write_text(to_geojson(unary_union(footprints)))
 keepouts=[x_prism(access_profile(y).buffer(2.4,quad_segs=8),0,220) for y in FIXINGS]
 cavities=[];cavity_records=[]
 for i,z in enumerate([1.2,8.8,16.4]):
  pieces=[]
  for poly in footprints:
   air=prism(np.asarray(poly.exterior.coords)[:-1],z,6.4)
   # Clip to protected bevel rims and fastener tunnel walls.
   if i!=1:
    relevant=guards[0::2] if i==0 else guards[1::2]
    for g in relevant:
     air=safe_cut(air,g)
   for ko in keepouts:air=safe_cut(air,ko)
   if air is not None and air.Volume()>.01:pieces.extend(air.Solids())
  cavities.extend(pieces)
  cavity_records.append({'band_z_mm':[z,z+6.4],'cavity_count':len(pieces),'void_volume_cm3':sum(a.Volume() for a in pieces)/1000})
  print('Prepared compartment band',i+1,'cells',len(pieces),flush=True)
 result=outer.cut(cq.Compound.makeCompound(cavities))
 print('Compartmented body complete',flush=True)
 for y in FIXINGS:
  result=result.cut(x_prism(access_profile(y),LAND,220))
  # Small screw clearance also has a 45-degree upper relief for side printing.
  bore=access_profile(y,radius=2.6,roof_z=12+2.6*2**.5,round_top=0)
  result=result.cut(x_prism(bore,-1,LAND+1.01))
 print('Fastener access complete',flush=True)
 # Save an actual mid-air-band section for checking and drawing.
 cutaway=result.intersect(cq.Solid.makeBox(250,230,4.4,cq.Vector(-5,-40,0)))
 cq.exporters.export(cutaway,str(D/'cutaway.stl'),tolerance=.04,angularTolerance=.1)
 (D/'dfm-build.json').write_text(json.dumps({'bands':cavity_records,'footprint_count':len(footprints),
  'cell_clear_box_mm':10,'divider_mm':1.2,'full_cell_corner_radius_mm':2,
  'roof_bridge_any_direction_upper_bound_mm':10*2**.5,'screw_axes_y_mm':FIXINGS,
  'land_from_wall_mm':LAND,'screw_clearance_diameter_mm':5.2,'tool_access_nominal_diameter_mm':16,
  'access_roof_cap_z_mm':22.4,'access_roof_remaining_skin_mm':1.6,
  'plate_z_intervals_mm':[[0,1.2],[7.6,8.8],[15.2,16.4],[22.8,24]],
  'limitations':['Cell bound is geometry, not a measured sliced extrusion span.','No strength credit assigned to manufacturing dividers.','Access openings interrupt the plates locally; prior E6 load calculations do not validate E7.']},indent=2))
 assert result.isValid(),'Invalid final solid'
 assert len(result.Solids())==1,'Disconnected bracket'
 cq.exporters.export(result,str(D/'bracket.step'))
 # Match the existing single-P1S orientation.
 printed=result.rotate((0,0,0),(0,0,1),180).translate((250,182,0))
 cq.exporters.export(printed,str(D/'bracket.stl'),tolerance=.02,angularTolerance=.08)
 cq.exporters.export(result,str(D/'mounted.stl'),tolerance=.02,angularTolerance=.08)
 record={'revision':'E7','chamfer_mm':CHAMFER,'body_corner_fillet_mm':2,'width_mm':WIDTH,'face_and_internal_plate_mm':FACE,
 'profile_simplification_tolerance_mm':TOL,'selected_chamfer_edges':2*len(edge_specs),'fade_run_mm':20,'fade_curve':'quintic Bezier; C2 at zero/full depth','fade_endpoints':[[fs,fe] for a,b,fs,fe in edge_specs],'paired_outline_edges':[[a.tolist(),b.tolist()] for a,b in pairs],
 'bevel_rim_keepout_distance_mm':guard_distance,'minimum_design_ligament_mm':FACE,'rim_guard_extra_mm':guard_extra,
 'valid_brep':result.isValid(),'solid_count':len(result.Solids()),'material_volume_cm3':result.Volume()/1000,
 'limitations':['Compartment geometry checked; no sliced-path or physical print validation, snap-force test, structural load or creep rating.','Thin snap fingers and small functional edges are excluded from the 3 mm chamfer.']}
 (D/'finish-verification.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)
