"""Continuous 2 mm face chamfers applied after the R2 side profile.
Structural joints keep full depth. Only thin retainer regions use runouts.
"""
import numpy as np
import cadquery as cq
import tempfile,hashlib,json
from pathlib import Path
from shapely.geometry import Polygon
S=np.hypot(100,12);q=np.sqrt(112.4**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S
rots=[np.arctan2(cy,cx-90)-np.pi/2,np.arctan2(cy-12,cx-190)-np.pi/2]
CHAMFER_ANGLE_DEG=50.
RISE_PER_INSET=float(np.tan(np.deg2rad(CHAMFER_ANGLE_DEG)))
def depth(v):
 d=2.
 for c,rot in zip([np.array([90,0]),np.array([190,12])],rots):
  w=v-c;r=np.linalg.norm(w);a=np.arctan2(w[1],w[0])-rot-1.5*np.pi;a=abs(np.arctan2(np.sin(a),np.cos(a)))*180/np.pi
  u=np.clip((75-a)/30,0,1);u=u**3*(10-15*u+6*u*u)
  radial=np.clip((r-18)/1.5,0,1);radial=radial**3*(10-15*radial+6*radial*radial)
  d=min(d,2*(u+(1-u)*radial))
 return d

def finish(body,p):
 if not Polygon(p).exterior.is_ccw:p=p[::-1]
 # Extra subdivision on long edges where finger runouts might occur.
 pts=[]
 def sample(a,c,level=0):
  m=(a+c)/2
  if level<14 and (np.linalg.norm(c-a)>2 or abs(depth(m)-(depth(a)+depth(c))/2)>.002):
   sample(a,m,level+1);sample(m,c,level+1)
  else:pts.append(a)
 for a,c in zip(p,np.roll(p,-1,axis=0)):sample(a,c)
 p=np.array(pts);ds=np.array([depth(v) for v in p]);cutters=[];spec=[]
 ds=np.where(ds<.005,0.,ds)
 for i,(a,c) in enumerate(zip(p,np.roll(p,-1,axis=0))):
  da=ds[i];dc=ds[(i+1)%len(p)]
  if max(da,dc)<1e-5:continue
  t=(c-a)/np.linalg.norm(c-a);n=np.array([-t[1],t[0]]);L=np.linalg.norm(c-a)
  prev=(a-p[i-1]);prev/=np.linalg.norm(prev);nxt=p[(i+2)%len(p)]-c;nxt/=np.linalg.norm(nxt)
  def ext(u,v,d):return d*abs(np.linalg.det(np.column_stack([u,v])))/(1+u@v)+.001
  ea=ext(prev,t,da);ec=ext(t,nxt,dc);outside=3.
  def V(s,z):
   xy=a+s*t-outside*n;return cq.Vector(*xy,z)
  wire=cq.Wire.makePolygon([V(-ea,(outside+da)*RISE_PER_INSET),V(L+ec,(outside+dc)*RISE_PER_INSET),V(L+ec,-outside),V(-ea,-outside)],close=True)
  cutters.append(cq.Solid.extrudeLinear(wire,[],cq.Vector(*(2*outside*n),-2*outside*RISE_PER_INSET)))
  spec.append({'a':a.tolist(),'b':c.tolist(),'depth_start_mm':float(da),'depth_end_mm':float(dc)})

 cache_key=hashlib.sha256(json.dumps([CHAMFER_ANGLE_DEG,spec,p.tolist()],sort_keys=True).encode()).hexdigest()[:16]
 for top in [False]:
  checkpoint=Path(tempfile.gettempdir())/f'rack-e11-bevel-{cache_key}-{int(top)}.brep'
  if checkpoint.exists():
   body=cq.importers.importBrep(str(checkpoint)).val();assert body.isValid()
   print('Restored chamfer face',top,flush=True);continue
  tools=[c.mirror('XY').translate((0,0,24)) for c in cutters] if top else cutters
  for i in range(0,len(tools),24):
   batch=tools[i:i+24]
   candidate=body.cut(*batch)
   if not candidate.isValid():candidate=candidate.fix()
   if not candidate.isValid():
    # Fuzzy tolerance is far below the 0.005 mm profile simplification.
    # Retry the same subtraction; never discard structural geometry.
    candidate=body.cut(*batch,tol=1e-5).fix()
   if not candidate.isValid():
    cq.exporters.export(candidate,str(checkpoint.with_suffix('.failed.brep')))
    raise ValueError(('Invalid bevel batch',top,i))
   body=candidate
   print('Chamfer cutters',min(i+24,len(tools)),'/',len(tools),flush=True)
  cq.exporters.export(body,str(checkpoint))
  print('Continuous chamfer face complete',top,flush=True)
 solids=sorted(body.Solids(),key=lambda x:x.Volume(),reverse=True)
 offcuts=sum(s.Volume() for s in solids[1:])
 # Detached remnants within removed bevels are not printable islands.
 remnants=[{'volume_mm3':s.Volume(),'z_min':s.BoundingBox().zmin,'z_max':s.BoundingBox().zmax} for s in solids[1:]]
 print('Bevel remnants',remnants,flush=True)
 assert offcuts<2. and all(r['z_max']<2*RISE_PER_INSET+.01 or r['z_min']>24-2*RISE_PER_INSET-.01 for r in remnants),('Unexpected disconnected material',remnants)
 body=solids[0];assert body.isValid()
 # Mirror the finished half to guarantee identical face treatments.
 bb=body.BoundingBox()
 lower=body.intersect(cq.Solid.makeBox(bb.xlen+2,bb.ylen+2,12,cq.Vector(bb.xmin-1,bb.ymin-1,0)))
 body=lower.fuse(lower.mirror('XY').translate((0,0,24))).clean()
 assert body.isValid() and len(body.Solids())==1
 offcuts*=2
 return body,{'revision':'E11','chamfer_face_inset_mm':2,'chamfer_rise_mm':2*RISE_PER_INSET,'angle_above_bed_deg':CHAMFER_ANGLE_DEG,'width_mm':24,'order':['R6 rigid shoulder and R2 side-profile blends','extrude','continuous 50 degree face chamfers','fastener bores'],'mirroring':'Finished Z=0..12 half mirrored about Z=12 and fused before fastener cuts','runouts':'Only thin dowel-retainer regions; no structural edge-end fades','detached_bevel_remnants_removed_mm3':offcuts,'bevel_remnant_audit':remnants,'edges':spec}
