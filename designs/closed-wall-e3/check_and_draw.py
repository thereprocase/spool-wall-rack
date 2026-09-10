from pathlib import Path
import xml.etree.ElementTree as ET,re,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Circle
D=Path(__file__).resolve().parent

def polys(f):
 root=ET.parse(f).getroot();out=[]
 for e in root.findall('{http://www.w3.org/2000/svg}path'):
  for s in e.attrib['d'].split('M')[1:]:out.append(np.array([list(map(float,x)) for x in re.findall(r'(-?[\d.]+),(-?[\d.]+)',s)])*[1,-1])
 return out

def path(ps):
 verts=[];codes=[]
 for p in ps:verts.extend([*p,p[0]]);codes.extend([MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY])
 return MP(verts,codes)

def rotate(p,angle):
 a=math.radians(angle);return p@np.array([[math.cos(a),math.sin(a)],[-math.sin(a),math.cos(a)]])

def gap(ps,c,r):
 a=np.concatenate(ps);b=np.concatenate([np.roll(p,-1,axis=0) for p in ps]);v=b-a
 t=np.clip(((c-a)*v).sum(1)/np.maximum((v*v).sum(1),1e-12),0,1)
 return float((np.linalg.norm(a+t[:,None]*v-c,axis=1)-r).min())
ps=polys(D/'profile.svg');rp=polys(D/'retainer-profile.svg')
angle=math.degrees(math.acos(75/112.4));rotation=angle-90
ret=[rotate(p,rotation)+[76,0] for p in rp]
checks=[]
for diameter in np.arange(180,220.001,.1):
 R=diameter/2;h=math.sqrt((R+12.4)**2-75**2);c=np.array([151,h])
 checks.append((diameter,gap(ps,c,R),gap(ret,c,R),math.degrees(math.atan2(h,75))))
vals=np.array(checks);vv=np.concatenate(ps)
throat=2*((13+1.35/2)*math.cos(math.radians(19))-1.35/2)
report={'revision':'E3','status':'geometry prototype; no slicing, snap-force, fatigue, or strength validation',
 'reference_spool_diameter_mm':200,'rear_contact_angle_deg_from_positive_x':angle,'rear_bearing_seat_center_angle_deg':angle+180,
 'front_contact_angle_deg_from_positive_x':180-angle,'reference_contact_rotation_range_deg':vals[:,3].tolist()[::200],
 'root_transition':'C2 quintic radial blend; 25 to 75 degrees from bearing axis',
 'concave_root_fillet_mm':1.5,'convex_edge_round_mm':.45,'wrap_deg':218,'seat_diameter_mm':26,'finger_bending_thickness_mm':1.35,'bearing_radial_thickness_mm':6,
 'throat_mm_analytic_rounded_noses':throat,'nominal_total_throat_interference_mm':25.4-throat,
 'minimum_full_bracket_spool_clearance_mm':float(vals[:,1].min()),'minimum_retainer_spool_clearance_mm':float(vals[:,2].min()),
 'envelope_mm':[*list(vv.max(0)-vv.min(0)),24], 'structural_perimeter_mm':2.4,'outer_faces_mm':1.2,'internal_plates_mm':1.2,
 'assumptions':['Rigid nominal 25.4 mm rods, equal-radius flanges, 150 mm nominal seat spacing.','Rod seats 0.3 mm radially away from spool under contact load.','Reference direction is exact for 200 mm flanges; direction varies with flange diameter.','8 mm coupon is a fit/behavior sample and has one-third the width of the 24 mm bracket.','Finger movement and insertion path are not simulated; clearance result is for seated undeformed geometry.']}
assert len(ps)==1,'Disconnected outline or an unintended closed hole'
assert vals[:,1].min()>3,'Spool clearance failed'
(D/'verification.json').write_text(json.dumps(report,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(1,2,figsize=(15,7.5),facecolor='#f5f3ec',gridspec_kw={'width_ratios':[1.12,1]})
for ax in axes:ax.set_aspect('equal');ax.axis('off');ax.set_facecolor('#f5f3ec')
ax=axes[0];ax.add_patch(PathPatch(path(ps),fc='#267f80',ec='#164a53',lw=.7))
h=math.sqrt(112.4**2-75**2);C=np.array([151,h])
ax.add_patch(Circle(C,100,fill=False,ec='#879395',lw=1.4))
for x in [76,226]:
 n=(C-[x,0])/112.4;rod=np.array([x,0])-.3*n
 ax.add_patch(Circle(rod,12.7,fc='#d3b27a',ec='#977542'))
 contact=rod+12.7*n;bearing=rod-12.7*n
 ax.plot(*contact,'o',color='#ba5739',ms=4)
 ax.annotate('',xy=bearing-12*n,xytext=bearing+2*n,arrowprops={'arrowstyle':'->','lw':2,'color':'#ba5739'})
ax.set_xlim(-5,251);ax.set_ylim(-101,190)
ax.set_title('MIRRORED, LOAD-ALIGNED SEATS',loc='left',fontweight='bold',fontsize=13)
ax.text(0,-97,'200 mm reference spool • 150 mm seat centers',fontsize=10,color='#4d656b')
ax=axes[1];ax.add_patch(PathPatch(path(ret),fc='#267f80',ec='#164a53',lw=1))
n=(C-[76,0])/112.4;rod=np.array([76,0])-.3*n
ax.add_patch(Circle(rod,12.7,fc='#d3b27a',ec='#977542'))
contact=rod+12.7*n;bearing=rod-12.7*n
ax.plot([contact[0],bearing[0]],[contact[1],bearing[1]],'--',color='#ba5739',lw=1)
ax.plot(*contact,'o',color='#ba5739',ms=6)
ax.annotate('Spool contact / open sector',xy=contact,xytext=(82,29),arrowprops={'arrowstyle':'->','color':'#ba5739'},ha='center',fontsize=10)
ax.annotate('6 mm rigid bearing seat\n180° opposite contact',xy=bearing-2*n,xytext=(45,-26),arrowprops={'arrowstyle':'->','color':'#164a53'},fontsize=10)
for theta,label,pos in [(161,'1.35 mm flexible finger',(40,19)),(379,'Tangent rounded nose',(97,-14))]:
 p=rotate(np.array([[13.675*math.cos(math.radians(theta)),13.675*math.sin(math.radians(theta))]]),rotation)[0]+[76,0]
 ax.annotate(label,xy=p,xytext=pos,arrowprops={'arrowstyle':'->','color':'#164a53'},fontsize=10)
ax.annotate('',xy=np.array([76,0])+20*n,xytext=np.array([76,0])+29*n,arrowprops={'arrowstyle':'->','lw':2,'color':'#164a53'})
ax.set_xlim(38,123);ax.set_ylim(-34,34)
ax.set_title('REAR SEAT DETAIL',loc='left',fontweight='bold',fontsize=13)
fig.suptitle('E3 • CLEAN BEARING CONNECTIONS',x=.055,ha='left',fontsize=21,fontweight='bold',color='#233e45')
fig.text(.055,.025,'2.4 mm structural perimeter • 1.2 mm continuous plates • prototype geometry; insertion force and internal roof printing unresolved',fontsize=10,color='#4d656b')
fig.tight_layout(rect=[.025,.07,.99,.94]);fig.savefig(D/'retainer-engineering.png',dpi=160,facecolor=fig.get_facecolor())
print(json.dumps({k:v for k,v in report.items() if k!='assumptions'},indent=2))
