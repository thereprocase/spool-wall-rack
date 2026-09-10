"""E9 actual-outline drawing and STL cross-section of the finished chamfers."""
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
ax.annotate('',xy=(90,-45),xytext=(190,-45),arrowprops={'arrowstyle':'<->'});ax.text(140,-51,'100 mm horizontal',ha='center',fontsize=10)
for y in [164,40]:ax.plot([0,45],[y,y],ls='--',lw=.7,color='#453e31');ax.text(3,y+3,'Screw axis',fontsize=8)
ax.annotate('R2 at wall facet changes',xy=(17.5,82),xytext=(66,165),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.annotate('Reshaped back arm\nclears 180–220 mm spools',xy=(12,120),xytext=(65,205),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.set(xlim=(-8,240),ylim=(-57,240),aspect='equal',xlabel='Projection from wall (mm)',ylabel='Installed height (mm)',title='Actual E9 profile with nominal dowels and spool envelopes')
reader=vtk.vtkSTLReader();reader.SetFileName(str(D/'body-mounted.stl'));reader.Update();plane=vtk.vtkPlane();plane.SetOrigin(145,0,0);plane.SetNormal(1,0,0);cut=vtk.vtkCutter();cut.SetCutFunction(plane);cut.SetInputData(reader.GetOutput());cut.Update();mesh=cut.GetOutput();pts=vtk_to_numpy(mesh.GetPoints().GetData());lines=mesh.GetLines();lines.InitTraversal();ids=vtk.vtkIdList()
while lines.GetNextCell(ids):
 q=pts[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]];bx.plot(q[:,2],q[:,1],color='#194d53',lw=1.5)
bx.set(aspect='equal',xlabel='Printer Z / bracket width (mm)',ylabel='Installed height (mm)',title='Finished CAD section at X = 145 mm')
bx.set_xlim(-6,30);bx.set_ylim(-40,13);bx.axvline(0,lw=.7,color='#9ba6a0',ls='--');bx.axvline(24,lw=.7,color='#9ba6a0',ls='--')
bx.annotate('2 mm chamfer',xy=(1,-31),xytext=(5,-38),arrowprops={'arrowstyle':'->'},fontsize=10);bx.annotate('Mirrored 2 mm chamfer',xy=(23,1),xytext=(2,9),arrowprops={'arrowstyle':'->'},fontsize=10)
fig.suptitle('E9 / raised front rail • 2 mm face chamfers • R2 wall transitions',fontsize=17,fontweight='bold');fig.supxlabel('Outline and cross-section extracted from the generated design. Thin snap noses retain their smaller working radii.',fontsize=9)
fig.savefig(D/'engineering-drawing.png',dpi=160)
