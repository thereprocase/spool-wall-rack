"""Geometric envelope and section-property comparison; no material/load allowable."""
from pathlib import Path
import json, math, re, xml.etree.ElementTree as ET
import numpy as np
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle
D=Path(__file__).resolve().parent

def profile(folder):
 root=ET.parse(folder/'profile.svg').getroot()
 s=root.find('{http://www.w3.org/2000/svg}path').attrib['d']
 return np.array([list(map(float,x)) for x in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)',s)])*[1,-1]

def section(shape,x):
 dx=.2
 cut=shape.intersect(cq.Solid.makeBox(dx,400,60,cq.Vector(x-dx/2,-120,-10)))
 props=GProp_GProps();BRepGProp.VolumeProperties_s(cut.wrapped,props)
 area=props.Mass()/dx;c=props.CentreOfMass();I=props.MatrixOfInertia().Value(3,3)/dx-area*dx*dx/12
 bb=cut.BoundingBox();extreme=max(bb.ymax-c.Y(),c.Y()-bb.ymin)
 return {'x_from_wall_mm':x,'area_mm2':area,'centroid_y_mm':c.Y(),'depth_mm':bb.ylen,'I_about_width_axis_mm4':I,'minimum_elastic_section_modulus_mm3':I/extreme}

out={'status':'Geometric section comparison only; same elastic modulus assumed for EI ratios. No global deflection, allowable load or creep calculation.','revisions':{}}
layout={'E4':(76,226),'E5':(76,226),'E6':(90,190)}
for rev in ['E4','E5','E6']:
 folder=D.parent/('closed-wall-'+rev.lower());p=profile(folder)
 rear,front=layout[rev];half=(front-rear)/2
 shape=cq.importers.importStep(str(folder/'bracket.step')).val()
 wall=[f for f in shape.Faces() if abs(f.BoundingBox().xmin)<1e-4 and abs(f.BoundingBox().xmax)<1e-4]
 ymin=min(f.BoundingBox().ymin for f in wall);ymax=max(f.BoundingBox().ymax for f in wall)
 spool=[]
 for dia in [180,200,220]:
  h=math.sqrt((dia/2+12.4)**2-half**2);bottom=h-dia/2;top=h+dia/2
  spool.append({'spool_diameter_mm':dia,'spool_bottom_y_mm':bottom,'spool_top_y_mm':top,'extension_below_spool_mm':max(0,bottom-p[:,1].min()),'extension_above_spool_mm':max(0,p[:,1].max()-top),'combined_rack_height_mm':max(top,p[:,1].max())-min(bottom,p[:,1].min())})
 out['revisions'][rev]={'bracket_height_mm':float(np.ptp(p[:,1])),'back_contact_extent_y_mm':[ymin,ymax],'back_contact_area_mm2':sum(f.Area() for f in wall),'upper_screw_to_lowest_back_contact_mm':(164 if rev=='E6' else 138)-ymin,'rail_spacing_mm':front-rear,'sections':[section(shape,x) for x in [(rear+front)/2]],'reference_cradle_escape_rise_mm':112.7*(1-math.sqrt(112.4**2-half**2)/112.4),'spool_envelopes':spool}
 print(rev,'checked',flush=True)
a=out['revisions']['E4'];b=out['revisions']['E6']
I4=a['sections'][0]['I_about_width_axis_mm4'];I6=b['sections'][0]['I_about_width_axis_mm4']
out['E6_to_E4_midspan_I_ratio']=I6/I4
out['E6_to_E4_prismatic_forearm_stiffness_proxy']=(I6/I4)*(150/100)**3
out['E6_to_E4_idealized_upper_screw_tension_ratio_same_total_vertical_load']=(140/151)*a['upper_screw_to_lowest_back_contact_mm']/b['upper_screw_to_lowest_back_contact_mm']
out['assumptions']=['Perfectly flat wall. Geometric contact area is not uniformly loaded bearing area.','Screw-tension ratio assumes equal total vertical loads shared equally between rods, a point compression reaction at the lowest wall contact and all overturning tension at the upper screw. The load arm changes from 151 to 140 mm; actual contact and bolt forces require analysis.','Section properties use 0.2 mm slices of the final CAD with all modeled solid filled and all air volumes empty. Infill gets zero strength credit.','The I/L^3 stiffness proxy treats each forearm as a uniform beam with its midpoint section and span equal to rail spacing. Actual sections vary and snap roots, wall leg, connection compliance, shear, anisotropy, buckling and creep are excluded. It is not whole-bracket stiffness.', 'Cradle escape rise is the ideal center-of-mass rise to pass vertically above one nominal rod, without friction, finger movement or spool deformation. It indicates reduced rocking resistance, not a handling qualification.']
(D/'vertical-verification.json').write_text(json.dumps(out,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig,axes=plt.subplots(1,2,figsize=(14,8),facecolor='#f5f3ec')
for ax,rev in zip(axes,['E4','E6']):
 rear,front=layout[rev];half=(front-rear)/2;mid=(rear+front)/2
 h=math.sqrt(112.4**2-half**2);bottom=h-100
 folder=D.parent/('closed-wall-'+rev.lower());p=profile(folder);lo=p[:,1].min();hi=p[:,1].max()
 ax.set_aspect('equal');ax.axis('off');ax.set_xlim(-50,324);ax.set_ylim(-109,220)
 ax.add_patch(Rectangle((-12,-99),12,310,fc='#dedfd9',ec='#a0aaa9',hatch='///',lw=.5))
 ax.add_patch(Polygon(p,fc='#267f80',ec='#164a53',lw=.7))
 ax.add_patch(Circle((mid,h),100,fc='#e7d8b9',ec='#a38f69',alpha=.55,lw=1))
 for x in [rear,front]:
  n=(np.array([mid,h])-[x,0])/112.4;c=np.array([x,0])-.3*n
  ax.add_patch(Circle(c,12.7,fc='#d3b27a',ec='#977542',lw=1))
 for y,length in [((164 if rev=='E6' else 138),20),(12,60)]:
  ax.plot([0,length],[y,y],color='#e2bd72',lw=2)
 ax.axhline(bottom,xmin=.14,xmax=.93,color='#9f775a',ls='--',lw=.9)
 ax.annotate('',xy=(-29,hi),xytext=(-29,lo),arrowprops={'arrowstyle':'<->','color':'#243d43'})
 ax.text(-34,(hi+lo)/2,f'{hi-lo:.0f} mm body',rotation=90,ha='right',va='center',color='#243d43')
 ax.annotate('',xy=(269,bottom),xytext=(269,lo),arrowprops={'arrowstyle':'<->','color':'#a95737'})
 ax.text(274,(lo+bottom)/2,f'{bottom-lo:.1f} mm',ha='left',va='center',fontsize=10,color='#a95737')
 ax.text(mid,h+8,'Ø200 mm spool',ha='center',color='#665941',fontsize=13)
 ax.text(mid,h-10,'Nominal seated position',ha='center',color='#665941',fontsize=9)
 ax.text(-8,211,'WALL',fontsize=9,color='#667779')
 ax.set_title(rev+' / '+('PREVIOUS DEEP ARM' if rev=='E4' else 'SHORTER SPAN'),loc='left',fontweight='bold',fontsize=14,color='#233e45')
 ax.text(8,-100,('Clipped toe; back contact ends above arm underside' if rev=='E4' else '100 mm rail spacing; 208 mm full-height flat back'),fontsize=10,color='#4d656b')
fig.suptitle('A shorter span saves 40 mm of loaded rack height',x=.06,ha='left',fontsize=23,fontweight='bold',color='#233e45')
fig.text(.06,.025,'Actual CAD profiles • same Ø200 spool and scale • 150 → 100 mm rail spacing • handling and load tests pending',fontsize=11,color='#4d656b')
fig.tight_layout(rect=[.035,.065,.98,.94]);fig.savefig(D/'vertical-comparison.png',dpi=160,facecolor=fig.get_facecolor())
print(json.dumps(out,indent=2))
