"""Check E10 raised-rail fit and actual finished chamfers/R2 wall transitions."""
from pathlib import Path
import re,json,math,xml.etree.ElementTree as ET
import numpy as np
import cadquery as cq
from shapely.geometry import Polygon,Point
D=Path(__file__).resolve().parent
root=ET.parse(D/'profile.svg').getroot();s=root.find('{http://www.w3.org/2000/svg}path').attrib['d']
p=np.array([[float(a),-float(b)] for a,b in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)]);poly=Polygon(p)
assert poly.is_valid
shape=cq.importers.importStep(str(D/'body-only.step')).val().translate((-250,-182,0)).rotate((0,0,0),(0,0,1),180)
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
classifier=BRepClass3d_SolidClassifier(shape.wrapped)
def contains(xyz):
 classifier.Perform(gp_Pnt(*map(float,xyz)),1e-6)
 return classifier.State()==TopAbs_IN or classifier.IsOnAFace()
rows=[]
# Dowel center model spans nominal support and 0.3 mm radial seat-clearance sensitivity.
for radius in [12.4,12.7]:
 for diameter in np.arange(180,220.001,.25):
  S=math.hypot(100,12);q=math.sqrt((diameter/2+radius)**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S
  clear=poly.distance(Point(cx,cy))-diameter/2
  rows.append({'spool_mm':float(diameter),'effective_rail_radius_mm':radius,'clearance_mm':clear,'center_mm':[cx,cy]})
worst=min(rows,key=lambda a:a['clearance_mm']);assert worst['clearance_mm']>=3.45,worst
spec=json.loads((D/'finish-specification.json').read_text());checks=[]
probe_junctions=np.array([[0,176],[0,-32],[190,-32],[110,-2.4],[66,6],[30,48],[17.5,82],[12,108],[12,128],[18,176]],float)
for index,edge in enumerate(spec['edges']):
 if min(edge['depth_start_mm'],edge['depth_end_mm']) < 1.999:continue
 a=np.array(edge['a']);b=np.array(edge['b']);m=(a+b)/2
 if index%20 and np.linalg.norm(probe_junctions-m,axis=1).min()>3:continue
 t=(b-a)/np.linalg.norm(b-a);n=np.array([-t[1],t[0]])
 if not poly.contains(Point(*(m+.1*n))):n=-n
 # Full-depth segments include short edges through the pre-existing R2 blends.
 rec={'midpoint_xy_mm':m.tolist(),'length_mm':float(np.linalg.norm(b-a)),'face_checks':[]}
 for top in [False,True]:
  # q+z <2 must be cut; q+z >2 must remain on an intact structural edge.
  for q,z,expected in [(.5,1.,False),(.5,2.,True),(1.5,.75,True)]:
   xy=m+q*n;Z=24-z if top else z
   # Near corners the neighboring edge can govern the bevel too.
   distance=poly.boundary.distance(Point(*xy))
   expected=bool(poly.contains(Point(*xy)) and distance>max(0,2-z))
   if abs(distance-max(0,2-z))<.02:continue
   inside=contains((xy[0],xy[1],Z))
   rec['face_checks'].append({'top':top,'inset_mm':q,'depth_from_face_mm':z,'expected_material':expected,'actual_material':inside})
   assert inside==expected,(rec,q,z,expected,inside)
 checks.append(rec)
# Full depth at structural joints; zero chamfer within the flexible fingers.
from continuous_chamfer import depth,rots
junctions=[[0,176],[0,-32],[190,-32],[110,-2.4],[66,6],[30,48],[17.5,82],[12,108],[12,128],[18,176]]
for xy in junctions:assert depth(np.array(xy))==2,xy
finger_checks=[]
for center,rotation in zip([np.array([90,0]),np.array([190,12])],rots):
 for local in [168,372]:
  a=math.radians(local)+rotation;xy=center+13.675*np.array([math.cos(a),math.sin(a)])
  assert poly.contains(Point(*xy)),xy
  assert depth(xy)==0,xy
  for z in [.3,23.7]:
   ok=contains((*xy,z));assert ok,(xy,z)
   finger_checks.append({'xy_mm':xy.tolist(),'print_z_mm':z,'material_preserved':ok})
# Fit actual sampled arc points around nominal R2 fillets at body facet junctions.
vertices=np.array([[0,176],[0,-32],[190,-32],[190,7.2],[110,-2.4],[66,6],[30,48],[17.5,82],[12,108],[12,128],[18,176]],float)
fillets=[]
for k in [6,7,8,9,10]:
 v=vertices[k];prev=vertices[k-1];nxt=vertices[(k+1)%len(vertices)];u=(v-prev)/np.linalg.norm(v-prev);w=(nxt-v)/np.linalg.norm(nxt-v);cross=np.linalg.det(np.column_stack([u,w]));sgn=1 if cross>0 else -1
 n1=np.array([-u[1],u[0]]);n2=np.array([-w[1],w[0]]);rhs=sgn*2*(n2-n1);sol=np.linalg.solve(np.column_stack([u,-w]),rhs);center=v+sgn*2*n1+sol[0]*u
 dist=np.linalg.norm(p-center,axis=1)
 theta0=math.atan2(*(-sgn*n1)[::-1]);theta1=math.atan2(*(-sgn*n2)[::-1]);turn=math.atan2(math.sin(theta1-theta0),math.cos(theta1-theta0));angles=np.arctan2(p[:,1]-center[1],p[:,0]-center[0]);da=np.arctan2(np.sin(angles-theta0),np.cos(angles-theta0))
 # Exclude tangent-line extensions: they can lie close to the nominal circle
 # but bias a radius fit, particularly at shallow direction changes.
 angular=(da>.005)&(da<turn-.005) if turn>0 else (da<-.005)&(da>turn+.005)
 candidates=p[angular&(np.linalg.norm(p-v,axis=1)<4)]
 assert len(candidates)>=4,(v,len(candidates))
 A=np.column_stack([2*candidates[:,0],2*candidates[:,1],np.ones(len(candidates))]);b=(candidates*candidates).sum(1);cx,cy,c=np.linalg.lstsq(A,b,rcond=None)[0];rad=math.sqrt(c+cx*cx+cy*cy)
 err=abs(np.linalg.norm(candidates-[cx,cy],axis=1)-rad).max()
 fillets.append({'vertex_mm':v.tolist(),'sample_points':len(candidates),'nominal_radius_mm':2,'unconstrained_fitted_radius_mm':rad,'max_radial_fit_error_mm':float(err),'max_deviation_from_nominal_R2_mm':float(abs(np.linalg.norm(candidates-center,axis=1)-2).max())})
 assert fillets[-1]['max_deviation_from_nominal_R2_mm']<.01,fillets[-1]
# Washer support and nominal center locations, independent of zero-collision envelope checks.
def cyl(r,x,L,y):return cq.Solid.makeCylinder(r,L,cq.Vector(x,y,12),cq.Vector(1,0,0))
land=[]
for y in [164,40]:
 annulus=cyl(6.5,.1,3.4,y).cut(cyl(2.75,0,3.6,y));fraction=shape.intersect(annulus).Volume()/annulus.Volume();assert fraction>.98
 land.append({'y_mm':y,'support_fraction':fraction,'clamping_mm':3.6})
report={'revision':'E10','front_lift_mm':12,'rear_center_mm':[90,0],'front_center_mm':[190,12],'profile_area_mm2':poly.area,'minimum_flange_clearance':worst,'spool_sweep_cases':len(rows),'chamfer_mm':2,'mirrored_chamfer_checks':checks,'body_R2_arc_checks':fillets,'structural_junctions_full_chamfer':junctions,'finger_material_checks':finger_checks,'washer_landings':land,'limitations':['Nominal seated 2D flange sweep; not insertion or loaded/deformed contact validation.','Thin snap noses retain their separately dimensioned radii, not a blanket R2.','The wall contact strip ends retain square contact corners; exposed body-facet transitions are R2.','E9 FEM is a prior-finish baseline, not an exact solve of E10.']}
(D/'engineering-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
