"""E13 actual-outline drawing and STL cross-section of the finished chamfers."""
from pathlib import Path
import re,json,xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle
import vtk
from vtk.util.numpy_support import vtk_to_numpy
D=Path(__file__).resolve().parent
root=ET.parse(D/'profile.svg').getroot();s=root.find('{http://www.w3.org/2000/svg}path').attrib['d'];p=np.array([[float(a),-float(b)] for a,b in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)])
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,8),gridspec_kw={'width_ratios':[1.6,1]},layout='constrained');fig.set_facecolor('#f3f1e9')
for a in [ax,bx]:a.set_facecolor('#f3f1e9')
ax.add_patch(Polygon(p,fc='#367d80',ec='#194d53',lw=.7))
for x,y in [(90,0),(190,12)]:ax.add_patch(Circle((x,y),12.7,fc='#d5b576',ec='#967346',lw=1))
for diameter,color in [(200,'#b6c9cc'),(220,'#91a5aa')]:
 S=np.hypot(100,12);q=np.sqrt((diameter/2+12.7)**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S
 ax.add_patch(Circle((cx,cy),diameter/2,fc=color,ec='#667c82',alpha=.19,lw=1.2))
ax.annotate('',xy=(214,12),xytext=(214,0),arrowprops={'arrowstyle':'<->','color':'#9b5c20'});ax.text(219,6,'+12 mm',va='center',fontsize=10,color='#9b5c20');ax.plot([190,217],[12,12],lw=.7,color='#9b5c20');ax.plot([90,217],[0,0],lw=.7,color='#9b5c20',ls='--')
ax.annotate('',xy=(90,-84),xytext=(190,-84),arrowprops={'arrowstyle':'<->'});ax.text(140,-90,'100 mm horizontal',ha='center',fontsize=10)
for y in [164,40]:ax.plot([0,45],[y,y],ls='--',lw=.7,color='#453e31');ax.text(3,y+3,'Screw axis',fontsize=8)
ax.annotate('30.0 mm section depth\n11 mm added below arm',xy=(90,-36),xytext=(2,-65),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.annotate('Reshaped back arm\nclears 180–220 mm spools',xy=(12,120),xytext=(65,205),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.set(xlim=(-8,240),ylim=(-95,240),aspect='equal',xlabel='Projection from wall (mm)',ylabel='Installed height (mm)',title='Actual E13 profile with nominal dowels and spool envelopes')
reader=vtk.vtkSTLReader();reader.SetFileName(str(D/'body-mounted.stl'));reader.Update();plane=vtk.vtkPlane();plane.SetOrigin(90,0,0);plane.SetNormal(1,0,0);cut=vtk.vtkCutter();cut.SetCutFunction(plane);cut.SetInputData(reader.GetOutput());cut.Update();mesh=cut.GetOutput();pts=vtk_to_numpy(mesh.GetPoints().GetData());lines=mesh.GetLines();lines.InitTraversal();ids=vtk.vtkIdList()
while lines.GetNextCell(ids):
 q=pts[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]];bx.plot(q[:,2],q[:,1],color='#194d53',lw=1.5)
bx.set(aspect='equal',xlabel='Printer Z / bracket width (mm)',ylabel='Installed height (mm)',title='Finished section through inner seat, X = 90 mm')
section_lo=float(pts[:,1].min());section_hi=float(pts[:,1].max())
bx.set_xlim(-6,30);bx.set_ylim(section_lo-12,section_hi+10);bx.axvline(0,lw=.7,color='#9ba6a0',ls='--');bx.axvline(24,lw=.7,color='#9ba6a0',ls='--')
for a,b in [(0,1.2),(7.6,8.8),(15.2,16.4),(22.8,24)]:
 bx.fill_between([a,b],[section_lo+2.5]*2,[section_hi-2.5]*2,color='#b2c9c0',alpha=.5)
bx.annotate('50° to bed plane',xy=(1,section_lo+1),xytext=(1,section_lo-8),arrowprops={'arrowstyle':'->'},fontsize=10)
bx.annotate('Mirrored 50° bevel',xy=(23,section_hi-1),xytext=(-3,section_hi+6),arrowprops={'arrowstyle':'->'},fontsize=10)
bx.text(12,(section_lo+section_hi)/2,'Four continuous\n1.2 mm solid plates',ha='center',fontsize=10)
fig.suptitle('E13 / slim inner seat • 11 mm reinforcement • 50° face chamfers',fontsize=16,fontweight='bold');fig.supxlabel('Actual finished outline and section. Shaded bands locate the slicer-generated plates; the CAD body is a solid envelope.',fontsize=9)
fig.savefig(D/'engineering-drawing.png',dpi=160)
