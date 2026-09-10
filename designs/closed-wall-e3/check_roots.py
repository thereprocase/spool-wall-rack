from pathlib import Path
import json,math,re,xml.etree.ElementTree as ET
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
 v=[];c=[]
 for p in ps:v.extend([*p,p[0]]);c.extend([MP.MOVETO]+[MP.LINETO]*(len(p)-1)+[MP.CLOSEPOLY])
 return MP(v,c)

p=polys(D/'profile.svg')[0]
a=p-np.roll(p,1,axis=0);b=np.roll(p,-1,axis=0)-p
ln1=np.linalg.norm(a,axis=1);ln2=np.linalg.norm(b,axis=1)
turn=np.degrees(np.arctan2(a[:,0]*b[:,1]-a[:,1]*b[:,0],(a*b).sum(1)))
# Ignore microscopic edges from boolean tessellation when evaluating turn angles.
near=(np.linalg.norm(p-[226,0],axis=1)<23)&(ln1>.01)&(ln2>.01)
maxturn=float(abs(turn[near]).max())
u=np.linspace(0,1,20001);span=math.radians(50)
s=10*u**3-15*u**4+6*u**5;ds=30*u**2-60*u**3+30*u**4;dds=60*u-180*u**2+120*u**3
r=14.35+4.65*s;dr=-4.65*ds/span;ddr=4.65*dds/span**2
k=(r*r+2*dr*dr-r*ddr)/(r*r+dr*dr)**1.5
minR=float(1/abs(k).max())
rep={'revision':'E3','root_transition_continuity':'C2 in analytic radial profile; polygonal CAD approximation',
 'analytic_root_minimum_curvature_radius_mm':minR,'root_blend_endpoint_first_derivatives':[float(ds[0]),float(ds[-1])],
 'root_blend_endpoint_second_derivatives':[float(dds[0]),float(dds[-1])],
 'integrated_concave_blend_radius_mm':1.5,'convex_edge_round_mm':.45,
 'maximum_resolved_vertex_turn_deg_within_23mm_of_front_seat':maxturn,
 'vertex_turn_note':'Screening only; excludes adjacent polygon edges shorter than 0.01 mm. It is not an FEA stress concentration calculation.',
 'remaining_validation':['Slicer toolpaths for 1.35 mm curved fingers and their roots.','Curved-finger insertion/release strain and force.','Internal roof printing of the full bracket.']}
(D/'root-verification.json').write_text(json.dumps(rep,indent=2))
fig,axes=plt.subplots(1,2,figsize=(13,7.5),facecolor='#f5f3ec')
h=math.sqrt(112.4**2-75**2);n=np.array([-75,h])/112.4;rod=np.array([226,0])-.3*n
for ax,rev,col in zip(axes,['closed-wall-e2','closed-wall-e3'],['#89918c','#267f80']):
 ps=polys(D.parent/rev/'profile.svg');ax.set_aspect('equal');ax.axis('off');ax.set_facecolor('#f5f3ec')
 ax.add_patch(PathPatch(path(ps),fc=col,ec='#183f49',lw=.6))
 ax.add_patch(Circle(rod,12.7,fc='#d3b27a',ec='#977542',lw=.8))
 ax.set_xlim(202,250);ax.set_ylim(-25,23)
 ax.set_title('E2 · LEFTOVER SADDLE LIP' if rev.endswith('e2') else 'E3 · LIP REMOVED',loc='left',fontweight='bold',fontsize=14,color='#233e45')
axes[0].annotate('Old open-saddle lip\nhas no retaining function',xy=(215.5,-15.5),xytext=(204,-22),fontsize=10,color='#233e45',bbox={'facecolor':'#f5f3ec','edgecolor':'none','pad':3},arrowprops={'arrowstyle':'->','color':'#ba5739'})
axes[1].annotate('Arm joins the rigid seat\nwithout a second prong',xy=(234,-17),xytext=(204,-22),fontsize=10,color='#233e45',bbox={'facecolor':'#f5f3ec','edgecolor':'none','pad':3},arrowprops={'arrowstyle':'->','color':'#ba5739'})
fig.suptitle('FRONT SEAT • REMOVE THE LEGACY PRONG',x=.07,ha='left',fontsize=20,fontweight='bold',color='#233e45')
fig.text(.07,.07,'E3: smooth radial transition • R1.5 concave blends • R0.45 convex rounds • 1.35 mm working finger',fontsize=11,color='#4d656b')
fig.text(.07,.028,'Sections are from exported CAD profiles. Local stress, insertion force and printability are not yet validated.',fontsize=10,color='#4d656b')
fig.tight_layout(rect=[.04,.11,.98,.94]);fig.savefig(D/'root-comparison.png',dpi=170,facecolor=fig.get_facecolor())
print(json.dumps(rep,indent=2))
