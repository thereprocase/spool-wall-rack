"""Section properties of the finished, chamfered ideal printed material.

Integrate 120 layer-midpoint STL sections. Each layer's actual outline supplies
its contour walls; four complete 1.2 mm bands supply the continuous plates.
Sparse infill is removed and receives zero credit. This is EI/section-modulus
screening, not a stress-concentration factor, FFF constitutive model or rating.
"""
from pathlib import Path
import json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from shapely.geometry import LineString,Polygon
from shapely.ops import polygonize,unary_union,linemerge
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
LAYER=.2
XS=np.round(np.arange(55,135.001,.25),5)
SEAT=(77,103)
REFERENCES={'wall_side':(63,67),'outer_side':(113,117)}
MIN_I_RATIO=1.25
MIN_Z_RATIO=1.15

def parts(g):
 return list(g.geoms) if hasattr(g,'geoms') else [g]

def layer_polygons(mesh,z,inside_tester=None):
 plane=vtk.vtkPlane();plane.SetOrigin(0,0,z);plane.SetNormal(0,0,1)
 cut=vtk.vtkCutter();cut.SetInputData(mesh);cut.SetCutFunction(plane);cut.Update()
 m=cut.GetOutput();points=vtk_to_numpy(m.GetPoints().GetData())
 lines=m.GetLines();lines.InitTraversal();ids=vtk.vtkIdList();segs=[]
 while lines.GetNextCell(ids):
  xy=points[[ids.GetId(j) for j in range(ids.GetNumberOfIds())],:2]
  if np.linalg.norm(xy[-1]-xy[0])>1e-8:segs.append(LineString(xy))
 rings=list(polygonize(unary_union(segs)))
 assert rings,('No closed layer',z)
 # For whole-bracket work classify each polygon against the closed 3D mesh;
 # this retains separate layer islands without filling hardware-hole interiors.
 if inside_tester is not None:
  selected=[]
  for poly in rings:
   q=poly.representative_point()
   if inside_tester.IsInsideSurface(q.x,q.y,z):selected.append(poly)
  assert selected,('No classified material',z)
  return unary_union(selected)
 # The seat study region has no hardware holes. The main polygon contains the
 # complete structural section even where a screw tunnel separates a wall tip.
 main=max(rings,key=lambda p:p.area)
 assert main.is_valid and main.area>1000,(z,main.area)
 return main

def integrate(mesh,walls):
 t=.42+(walls-1)*(.45-.2*(1-np.pi/4))
 total=np.zeros((len(XS),3));ymin=np.full(len(XS),np.inf);ymax=-ymin.copy()
 plate_counts={str(a):0 for a in [0,7.6,15.2,22.8]}
 for k in range(120):
  z=(k+.5)*LAYER;poly=layer_polygons(mesh,z)
  band=next((a for a in [0,7.6,15.2,22.8] if a<z<a+1.2),None)
  solid=poly if band is not None else poly.difference(poly.buffer(-t,quad_segs=12))
  if band is not None:plate_counts[str(band)]+=1
  for j,x in enumerate(XS):
   line=LineString([(x,-150),(x,180)])
   spans=[g for g in parts(poly.intersection(line)) if g.geom_type=='LineString' and g.length>1]
   main=max(spans,key=lambda g:g.length)
   lo,hi=main.bounds[1],main.bounds[3]
   # Exclude disconnected snap-tip slivers from the beam section.
   section=solid.intersection(LineString([(x,lo),(x,hi)]))
   for g in parts(section):
    if g.geom_type!='LineString' or g.length<1e-7:continue
    a,b=g.bounds[1],g.bounds[3]
    total[j]+=LAYER*np.array([b-a,(b*b-a*a)/2,(b**3-a**3)/3])
    ymin[j]=min(ymin[j],a);ymax[j]=max(ymax[j],b)
  if k%20==0:print('Section layers',walls,k+1,'/120',flush=True)
 A,Q,J=total.T;yc=Q/A;I=J-Q*Q/A;Z=I/np.maximum(yc-ymin,ymax-yc)
 assert all(n==6 for n in plate_counts.values()),plate_counts
 return {'walls':walls,'wall_mm':t,'solid_layers_per_plate':plate_counts,
  'x_mm':XS.tolist(),'area_mm2':A.tolist(),'centroid_y_mm':yc.tolist(),
  'depth_mm':(ymax-ymin).tolist(),'I_z_mm4':I.tolist(),'min_section_modulus_mm3':Z.tolist()}

def summarize(r):
 I=np.array(r['I_z_mm4']);Z=np.array(r['min_section_modulus_mm3']);seat=(XS>=SEAT[0])&(XS<=SEAT[1]);out={}
 for label,(a,b) in REFERENCES.items():
  ref=(XS>=a)&(XS<=b)
  out[label]={'reference_band_mm':[a,b],'max_reference_I_mm4':float(I[ref].max()),
   'max_reference_Z_mm3':float(Z[ref].max()),'minimum_seat_I_ratio':float(I[seat].min()/I[ref].max()),
   'minimum_seat_Z_ratio':float(Z[seat].min()/Z[ref].max())}
 return {'seat_band_mm':list(SEAT),'minimum_seat_I_mm4':float(I[seat].min()),
  'minimum_seat_Z_mm3':float(Z[seat].min()),'I_minimum_x_mm':float(XS[seat][I[seat].argmin()]),
  'Z_minimum_x_mm':float(XS[seat][Z[seat].argmin()]),'comparisons':out}

def main():
 # Preserve the actual earlier measurements, then add the capped-depth revision.
 import hashlib
 rows=json.loads((D.parent/'closed-wall-e11/section-verification.json').read_text())['cases']
 reader=vtk.vtkSTLReader();reader.SetFileName(str(D/'body-mounted.stl'));reader.Update()
 measured_extra=-32-reader.GetOutput().GetBounds()[2]
 assert measured_extra<=38/3+.02,measured_extra
 for walls in [8,10]:
  row=integrate(reader.GetOutput(),walls);row['revision']='E12';row['summary']=summarize(row)
  baseline=next(r for r in rows if r['revision']=='E10' and r['walls']==walls)
  row['summary']['minimum_seat_I_vs_E10']=row['summary']['minimum_seat_I_mm4']/baseline['summary']['minimum_seat_I_mm4']
  row['summary']['minimum_seat_Z_vs_E10']=row['summary']['minimum_seat_Z_mm3']/baseline['summary']['minimum_seat_Z_mm3']
  assert row['summary']['minimum_seat_I_vs_E10']>1 and row['summary']['minimum_seat_Z_vs_E10']>1
  rows.append(row);print('E12',walls,row['summary'],flush=True)
 report={'method':__doc__,'layer_midpoint_mm':LAYER,'requested_added_depth_target_mm':9.5,'requested_added_depth_maximum_mm':38/3,'measured_finished_added_depth_mm':measured_extra,'source_STL_sha256':hashlib.sha256((D/'body-mounted.stl').read_bytes()).hexdigest(),
  'superseded_E11_I_ratio_gate':MIN_I_RATIO,'superseded_E11_Z_ratio_gate':MIN_Z_RATIO,
  'current_priority':'The explicit one-quarter target / one-third maximum added-depth request supersedes E11 adjacent-section margin targets. Report the resulting tradeoff without weakening adjacent arms.',
  'reference_selection':'Same seat and adjacent reference bands as E11; E10/E11 measurements are retained from their published audit.','cases':rows,
  'limitations':['Local EI and elastic section modulus do not measure notch stress concentration, bearing stress, creep or rupture strength.','Walls are ideal geometric offsets; actual variable-width toolpaths are checked separately.','E12 does not inherit the deeper E11 adjacent-section superiority claim.']}
 (D/'section-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 fig,axes=plt.subplots(2,1,figsize=(11,8),sharex=True,layout='constrained')
 for r in rows:
  for ax,key in zip(axes,['I_z_mm4','min_section_modulus_mm3']):
   ax.plot(XS,np.array(r[key])/1000,label=f"{r['revision']} / {r['walls']} walls",ls={'E10':'--','E11':':','E12':'-'}[r['revision']])
 for ax in axes:
  ax.axvspan(*SEAT,color='#dba140',alpha=.12)
  for a,b in REFERENCES.values():ax.axvspan(a,b,color='#577b87',alpha=.10)
  ax.grid(alpha=.2)
 axes[0].set_ylabel('Bending I (1000 mm^4)');axes[1].set_ylabel('Minimum section modulus (1000 mm^3)')
 axes[1].set_xlabel('Projection from wall X (mm)');axes[0].legend(ncols=3)
 fig.suptitle('E12 / quarter-depth reinforcement: finished section tradeoff')
 fig.savefig(D/'section-comparison.png',dpi=150)
 print('Requested depth cap and improvement over E10 pass',flush=True)

if __name__=='__main__':main()
