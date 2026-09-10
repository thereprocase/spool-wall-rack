"""Engineering views sectioned from the delivered mesh; hardware overlay is schematic."""
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle,Circle
D=Path(__file__).resolve().parent
r=vtk.vtkSTLReader();r.SetFileName(str(D/'mounted.stl'));r.Update()
def segments(origin,normal,axes,offset=(0,0)):
 p=vtk.vtkPlane();p.SetOrigin(*origin);p.SetNormal(*normal)
 c=vtk.vtkCutter();c.SetInputData(r.GetOutput());c.SetCutFunction(p);c.Update()
 m=c.GetOutput();points=vtk_to_numpy(m.GetPoints().GetData());lines=m.GetLines();lines.InitTraversal();ids=vtk.vtkIdList();out=[]
 while lines.GetNextCell(ids):
  for i in range(ids.GetNumberOfIds()-1):out.append(points[[ids.GetId(i),ids.GetId(i+1)]][:,axes]-offset)
 return out
bg='#f3f1e9';ink='#235d65';muted='#657d82';gold='#bf8740'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(15,10),facecolor=bg)
gs=fig.add_gridspec(2,2,width_ratios=[1.45,1],hspace=.48,wspace=.2)
a=fig.add_subplot(gs[:,0]);b=fig.add_subplot(gs[0,1]);c=fig.add_subplot(gs[1,1])
for ax in [a,b,c]:ax.set_aspect('equal');ax.set_facecolor(bg);ax.spines[['top','right']].set_visible(False);ax.tick_params(colors=muted)
a.add_collection(LineCollection(segments((0,0,12),(0,0,1),[0,1]),colors=ink,linewidths=.55))
a.set_xlim(-12,215);a.set_ylim(-43,184);a.set_xlabel('Distance from wall X / mm');a.set_ylabel('Installed height Y / mm')
a.set_title('MID-WIDTH SECTION · Z = 12 mm',loc='left',fontweight='bold')
for y in [164,40]:
 a.plot([-9,80],[y,y],'--',lw=.7,color=gold)
 a.text(76,y+4,f'Y = {y}',fontsize=9,color=gold)
a.annotate('Rounded 10 × 10 mm cells\n1.2 mm dividing walls',xy=(130,-15),xytext=(160,65),arrowprops={'arrowstyle':'->','color':muted},color=ink,ha='center')
a.annotate('Lower driver axis\nclears dowel seats',xy=(65,40),xytext=(125,117),arrowprops={'arrowstyle':'->','color':muted},color=ink,ha='center')
b.add_collection(LineCollection(segments((4,0,0),(1,0,0),[1,2],offset=(164,0)),colors=ink,linewidths=.8))
b.add_patch(Circle((0,12),6.5,fill=False,ec=gold,lw=1.5,ls='--'))
b.set_xlim(-13,13);b.set_ylim(-1,27);b.set_xlabel('Across access opening / mm');b.set_ylabel('Print Z / mm')
b.set_title('ACCESS ROOF · X = 4 mm',loc='left',fontweight='bold')
b.annotate('16 mm nominal clear circle\n13 mm washer envelope dashed',xy=(6,12),xytext=(0,25),fontsize=9,ha='center',arrowprops={'arrowstyle':'->','color':muted},color=ink)
b.text(0,2.5,'45° shoulders · short rounded roof cap',ha='center',fontsize=8,color=muted)
c.add_collection(LineCollection(segments((0,164,0),(0,1,0),[0,2]),colors=ink,linewidths=.8))
c.add_patch(Rectangle((3.6,5.5),1.2,13,fc=gold,alpha=.75))
c.add_patch(Rectangle((-7,9.585),12,4.83,fc=gold,alpha=.75))
c.add_patch(Rectangle((4.8,7.5),3,9,fc=gold,alpha=.75))
c.axvline(0,color=muted,lw=2);c.set_xlim(-8,27);c.set_ylim(-5,27)
c.set_xlabel('Distance from wall X / mm');c.set_ylabel('Print Z / mm')
c.set_title('UPPER FIXING · AXIAL SECTION',loc='left',fontweight='bold')
c.annotate('',xy=(0,-2),xytext=(3.6,-2),arrowprops={'arrowstyle':'<->','color':ink})
c.text(1.8,-4.3,'3.6 mm',ha='center',fontsize=9,color=ink)
c.text(15,20,'Ø5.2 clearance\n#8 / #10 / M5',ha='center',fontsize=10,color=ink)
c.text(16,6.5,'Hardware shown schematically',ha='center',fontsize=8,color=muted)
fig.suptitle('E7 / BRIDGE COMPARTMENTS + FASTENER ACCESS',x=.07,y=.97,ha='left',fontsize=21,fontweight='bold',color=ink)
fig.text(.07,.925,'Actual CAD sections · dimensions in mm · broad side on bed · geometry prototype',fontsize=11,color=muted)
fig.text(.07,.035,'Four 1.2 mm plates retained  |  14.2 mm maximum cavity diagonal  |  Toolpath and physical print checks remain',fontsize=10,color=muted)
fig.subplots_adjust(top=.86,bottom=.12,left=.07,right=.97)
fig.savefig(D/'dfm-engineering.png',dpi=160,facecolor=bg)
print('Engineering drawing complete',flush=True)
