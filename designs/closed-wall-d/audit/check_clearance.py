from pathlib import Path
import re,json,math
import numpy as np
from scipy.ndimage import distance_transform_edt
from matplotlib.path import Path as MPath
D=Path(__file__).resolve().parent.parent
s=(D/'bracket.stl').read_text();v=np.array([list(map(float,p)) for p in re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)',s)]).reshape(-1,3,3)
v[:,:,0]=250-v[:,:,0];v[:,:,1]=156-v[:,:,1]
def segments(z):
 a=[];b=[]
 for tri in v:
  hit=[]
  for p,q in zip(tri,np.roll(tri,-1,axis=0)):
   if (p[2]<z)!=(q[2]<z):hit.append(p[:2]+(q[:2]-p[:2])*(z-p[2])/(q[2]-p[2]))
  if len(hit)==2:a.append(hit[0]);b.append(hit[1])
 return np.array(a),np.array(b)
a,b=segments(.6);ab=b-a;ab2=(ab*ab).sum(1)
best=(1e9,None,None)
for diameter in np.arange(180,220.0001,.025):
 r=diameter/2;c=np.array([151,math.sqrt((r+12.7)**2-75**2)-.3])
 t=np.clip(((c-a)*ab).sum(1)/ab2,0,1);p=a+t[:,None]*ab
 dist=np.linalg.norm(p-c,axis=1)-r;i=dist.argmin()
 if dist[i]<best[0]:best=(float(dist[i]),float(diameter),p[i].tolist())
# Ray parity on an actual empty-band section. Determine air enclosed by exterior silhouette.
x,y=np.meshgrid(np.arange(0,244,.5),np.arange(-91,151,.5));pts=np.c_[x.ravel(),y.ravel()]
def interior(a,b):
 inside=np.zeros(len(pts),bool)
 for p,q in zip(a,b):
  if abs(q[1]-p[1])<1e-12:continue
  crosses=((p[1]>pts[:,1])!=(q[1]>pts[:,1]))&(pts[:,0]<p[0]+(pts[:,1]-p[1])*(q[0]-p[0])/(q[1]-p[1]))
  inside^=crosses
 return inside
outer=interior(a,b);ca,cb=segments(4.4);solid=interior(ca,cb)
air=(outer&~solid).reshape(x.shape);dt=distance_transform_edt(air)*.5;ij=np.unravel_index(dt.argmax(),dt.shape)
# Exact nearest-segment distance at the raster-selected center; this is an inscribed-circle witness, not a claimed optimal bridge direction.
c=np.array([x[ij],y[ij]]);ab=cb-ca;t=np.clip(((c-ca)*ab).sum(1)/(ab*ab).sum(1),0,1)
r=float(np.linalg.norm(ca+t[:,None]*ab-c,axis=1).min())
rep={'nominal_rigid_spool_diameters_mm':[180,220],'diameter_step_mm':.025,'min_clearance_mm':best[0],'worst_diameter_mm':best[1],'closest_bracket_point_xy_mm':best[2],
'actual_cavity_section_z_mm':4.4,'unsupported_inscribed_circle_center_xy_mm':c.tolist(),'unsupported_inscribed_circle_diameter_mm':2*r,
'limitations':['Nominal 25.4 mm straight rods; nominal saddle settlement 0.3 mm; rigid concentric spool flanges.','No screw heads, rod bending, spool wobble, tolerance stack or actual slicer toolpaths included.','Inscribed circle demonstrates a broad unsupported area. It is not a slicer bridge-length prediction.']}
(D/'audit/clearance-results.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep,indent=2))
