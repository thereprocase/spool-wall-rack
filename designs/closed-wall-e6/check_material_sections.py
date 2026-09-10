"""Sample final CAD beam sections at 12 kg; no material/load allowable."""
from pathlib import Path
import json, math
import cadquery as cq
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
D=Path(__file__).resolve().parent

def section(shape,x):
 dx=.2
 cut=shape.intersect(cq.Solid.makeBox(dx,400,60,cq.Vector(x-dx/2,-120,-10)))
 props=GProp_GProps();BRepGProp.VolumeProperties_s(cut.wrapped,props)
 area=props.Mass()/dx;c=props.CentreOfMass();I=props.MatrixOfInertia().Value(3,3)/dx-area*dx*dx/12
 bb=cut.BoundingBox();extreme=max(bb.ymax-c.Y(),c.Y()-bb.ymin)
 return {'x_from_wall_mm':x,'area_mm2':area,'centroid_y_mm':c.Y(),'depth_mm':bb.ylen,'I_about_width_axis_mm4':I,'minimum_elastic_section_modulus_mm3':I/extreme}

shape=cq.importers.importStep(str(D/'bracket.step')).val()
W=12*9.81;V=W/2;H=V*50/math.sqrt(112.4**2-50**2)
rows=[]
for x in [65,68,70,112,120,130,140,150,160,168]:
 q=section(shape,x)
 if x<90: moment=W*(140-x);axial=0
 else: moment=V*(190-x)+H*abs(q['centroid_y_mm']);axial=H
 q['moment_Nmm_at_12kg']=moment
 q['nominal_extreme_stress_MPa_at_12kg']=moment/q['minimum_elastic_section_modulus_mm3']+axial/q['area_mm2']
 rows.append(q);print(x,q['nominal_extreme_stress_MPa_at_12kg'],flush=True)
(D/'section-load-screen.json').write_text(json.dumps({'bracket_load_kg':12,'sections':rows,'limitations':['Nominal beam sections, not FEA or peak notch stresses.','Knee samples lie beyond modeled screw-head faces; actual fastener details remain to be checked.','Retainer neighborhoods are omitted because a beam-section assumption can incorrectly count unloaded finger material.','All modeled solid assumed filled; zero infill credit.']},indent=2))
