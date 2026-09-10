from pathlib import Path as FP
import xml.etree.ElementTree as ET,re,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch,Rectangle,Circle
from matplotlib.transforms import Affine2D
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
D=FP(__file__).resolve().parent

def read(name):
 r=ET.parse(D/name).getroot();out=[]
 for e in r.findall('{http://www.w3.org/2000/svg}path'):
  for t in e.attrib['d'].split('M')[1:]:
   out.append(np.array([list(map(float,q)) for q in re.findall(r'(-?[\d.]+),(-?[\d.]+)',t)])*[1,-1])
 return out

def path(ps):
 v=[];c=[]
 for p in ps:v.extend([*p,p[0]]);c.extend([Path.MOVETO]+[Path.LINETO]*(len(p)-1)+[Path.CLOSEPOLY])
 return Path(v,c)

def samples(ps,step=.1):
 out=[]
 for p in ps:
  for a,b in zip(p,np.roll(p,-1,axis=0)):
   n=max(1,int(np.ceil(np.linalg.norm(b-a)/step)))
   out.extend(a+(b-a)*np.arange(n)[:,None]/n)
 return np.array(out)
ps=read('profile.svg');hp=read('hollow-profile.svg');bd=samples(ps)
clear=[]
for diam in np.arange(180,220.01,.25):
 R=diam/2;h=math.sqrt((R+12.7)**2-75**2)-.3
 clear.append(float(np.linalg.norm(bd-[151,h],axis=1).min()-R))
plate_bd=-bd+[250,156]
lo=plate_bd.min(0);hi=plate_bd.max(0)
dx=np.maximum(0,np.maximum(-plate_bd[:,0],plate_bd[:,0]-18));dy=np.maximum(0,np.maximum(-plate_bd[:,1],plate_bd[:,1]-28))
ex=float(np.hypot(dx,dy).min())
assert min(clear)>2.8
assert np.all(lo>3) and np.all(hi<253) and ex>3
# Report any small through-openings; never hide unintended holes.
areas=[abs((p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)).sum()/2) for p in ps]
assert len(ps)==1, "Unexpected through-hole in the closed-wall profile"
# Longest contiguous cavity width in a representative closing layer along X/Y.
def inside(points,polys):
 m=np.zeros(len(points),bool)
 for p in polys:m^=Path(p).contains_points(points)
 return m
xx,yy=np.meshgrid(np.arange(0,245,.5),np.arange(-92,151,.5))
m=inside(np.c_[xx.ravel(),yy.ravel()],hp).reshape(xx.shape)
def max_run(row):
 dif=np.diff(np.r_[False,row,False].astype(int));s=np.flatnonzero(dif==1);e=np.flatnonzero(dif==-1)
 return (e-s).max(initial=0)*.5
max_x=max(max_run(row) for row in m);max_y=max(max_run(row) for row in m.T)
dist=distance_transform_edt(m)*.5
root_clear_diameter=float(dist.max()*2)
rep={'revision':'D','status':'geometry checked, no load rating, no slicing or physical validation',
 'single_envelope_mm':list((bd.max(0)-bd.min(0)))+[24],
 'p1s_xy_bounds_mm':[lo.tolist(),hi.tolist()], 'front_left_exclusion_gap_mm':ex,
 'min_nominal_spool_clearance_mm_approx':min(clear),'checked_flange_diameters_mm':[180,220],
 'sample_step_mm':.1,'planes_z_mm':[[0,1.2],[7.6,8.8],[15.2,16.4],[22.8,24]],
 'air_z_mm':[[1.2,7.6],[8.8,15.2],[16.4,22.8]],
 'outer_face_and_internal_plate_thickness_mm':1.2,'print_layer_mm':.2,
 'through_profile_contour_areas_mm2':areas,
 'cavity_max_axis_aligned_clear_runs_mm':{'x':max_x,'y':max_y},'largest_inscribed_cavity_diameter_mm_approx':root_clear_diameter,
 'mounting_hole_heights_mm':[138,12],'mounting_face_depths_mm':[20,60]}
(D/'verification.json').write_text(json.dumps(rep,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'text.color':'#223b43'})
fig=plt.figure(figsize=(14,9),facecolor='#f7f5ef')
ax=fig.add_axes([.04,.14,.51,.71]);ax.set_aspect('equal');ax.axis('off')
ax.add_patch(Rectangle((-10,-97),10,265,facecolor='#d5dbd5'))
ax.add_patch(PathPatch(path(ps),facecolor='#268a87',edgecolor='#155f5d',lw=1.3))
for y,deep in [(138,20),(12,60)]:
 ax.plot([0,deep+2],[y,y],color='#304b57',lw=2)
 ax.plot([deep,deep],[y-9,y+9],color='#304b57',lw=3)
for x in [76,226]:ax.add_patch(Circle((x,-.3),12.7,facecolor='#d2b37b',edgecolor='#94713f',lw=1.4))
R=100;h=math.sqrt(112.7**2-75**2)-.3
ax.add_patch(Circle((151,h),R,fill=False,edgecolor='#6e7c85',lw=1.5))
ax.add_patch(Circle((151,h),26,fill=False,edgecolor='#6e7c85',lw=1))
ax.annotate('Wall leg rises above the arm',xy=(12,115),xytext=(48,211),ha='left',fontsize=11,arrowprops={'arrowstyle':'->','color':'#496575'})
ax.annotate('Continuous plates run\nthrough the arm and knee',xy=(81,-49),xytext=(125,-102),ha='center',fontsize=11,arrowprops={'arrowstyle':'->','color':'#496575'})
ax.set_xlim(-16,260);ax.set_ylim(-119,222)
ax.set_title('MOUNTED SIDE VIEW',loc='left',fontsize=12,fontweight='bold')
# Exploded schematic: identical entire L-shaped profiles, offset in width.
ae=fig.add_axes([.58,.50,.39,.35]);ae.set_aspect('equal');ae.axis('off')
for i in [3,2,1,0]:
 tr=Affine2D().scale(.58,.60).skew_deg(0,5).translate(i*20,i*11)+ae.transData
 color='#238b88' if i in [0,3] else '#d29442'
 ae.add_patch(PathPatch(path(ps),facecolor=color,edgecolor='#fffdf7',lw=.9,transform=tr))
ae.set_xlim(-4,205);ae.set_ylim(-66,145)
ae.set_title('FOUR CONTINUOUS L-SHAPED PLATES',loc='left',fontsize=12,fontweight='bold')
ae.text(0,-64,'Exploded explanation · one monolithic print',fontsize=10)
# Actual through-width section, full-depth internal planes.
ac=fig.add_axes([.67,.19,.21,.25]);ac.set_aspect('equal');ac.axis('off')
ac.add_patch(Rectangle((0,0),24,27,facecolor='#fbfaf5',edgecolor='#1c706d',lw=1))
for a,b in [[0,1.2],[7.6,8.8],[15.2,16.4],[22.8,24]]:
 ac.add_patch(Rectangle((a,0),b-a,27,facecolor='#238b88' if a in [0,22.8] else '#d29442'))
for y in [0,25.65]:ac.add_patch(Rectangle((0,y),24,1.35,facecolor='#238b88'))
for x in [4.4,12,19.6]:ac.text(x,13.5,'6.4',ha='center',va='center',fontsize=10,rotation=90,color='#6f7979')
ac.annotate('',xy=(0,-3),xytext=(24,-3),arrowprops={'arrowstyle':'<->','color':'#496575'})
ac.text(12,-6,'24 mm bracket width',ha='center',fontsize=10)
ac.set_xlim(-2,26);ac.set_ylim(-8,29)
fig.text(.59,.465,'WIDTH SECTION · cavities stacked along printer Z',fontsize=11,fontweight='bold')
fig.text(.585,.145,'Every colored plane is 1.2 mm / six layers.\nThe three air gaps are each 6.4 mm.',fontsize=11,linespacing=1.7)
fig.text(.05,.945,'CONTINUOUS PLANES, LOADED IN THE LAYER PLANE',fontsize=20,fontweight='bold')
fig.text(.05,.895,'Revision D  ·  upward wall mount  ·  3 walls / 15% infill / 1.2 mm outside and internal faces',fontsize=12,color='#67797c')
fig.text(.05,.065,'Single-part P1S layout only. The internal plates are continuous through the entire L profile; no transverse cell grid.',fontsize=11)
fig.text(.05,.025,'Prototype geometry. Wide internal roofs require bridge validation. Previous material-specific load caps are withdrawn.',fontsize=10,color='#67797c')
fig.savefig(D/'design-section.png',dpi=170,facecolor=fig.get_facecolor())
print(json.dumps(rep,indent=2))
