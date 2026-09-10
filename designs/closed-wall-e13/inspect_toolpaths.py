"""Inspect actual OrcaSlicer G-code footprints; no printer connection.

Nominal bead footprints and path continuity do not validate adhesion, bridging,
curling, or a calibrated material process. Sparse infill receives no credit.
"""
from pathlib import Path
import json,re,zipfile,hashlib,xml.etree.ElementTree as ET
import numpy as np
import shapely
from shapely.geometry import LineString,box,Polygon
import vtk
from verify_sections import layer_polygons
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
D=Path(__file__).resolve().parent
WALL_ROLES={'Inner wall','Outer wall','Overhang wall','Gap infill'}
PLATE_BANDS=[(0,1.2),(7.6,8.8),(15.2,16.4),(22.8,24)]

def parse(folder):
 with zipfile.ZipFile(folder/'audit.3mf') as archive:
  model=ET.fromstring(archive.read('3D/3dmodel.model'))
  item=model.find('{*}build/{*}item')
  xf=np.array(list(map(float,item.attrib['transform'].split()))).reshape(4,3)
  rotation=xf[:3,:];offset=xf[3,:]
  assert np.allclose(rotation[:,2],[0,0,1],atol=1e-8),'Broad face no longer flat'
  assert np.allclose(rotation@rotation.T,np.eye(3),atol=1e-6),'Scaled slice'
 paths=[];widths=[];roles=[];layers=[];pos=np.zeros(3);role='Custom';width=.45;layer=-1
 for line in (folder/'plate_1.gcode').read_text().splitlines():
  if line.startswith(';Z:'):layer=int(round(float(line[3:])/.2))-1
  if line.startswith(';TYPE:'):role=line[6:]
  if line.startswith(';WIDTH:'):width=float(line[7:])
  code=line.split(';')[0].strip()
  if not re.match(r'^G[01](?: |$)',code):continue
  fields={k:float(v) for k,v in re.findall(r'([XYZE])([-+0-9.eE]+)',code)}
  new=pos.copy()
  for i,k in enumerate('XYZ'):
   if k in fields:new[i]=fields[k]
  if fields.get('E',0)>0 and np.linalg.norm(new[:2]-pos[:2])>1e-6:
   assert abs(new[2]-(layer+1)*.2)<.001,(new,layer)
   printed=(np.array([pos,new])-offset)@rotation.T
   mounted=np.column_stack([250-printed[:,0],182-printed[:,1]])
   paths.append(mounted);widths.append(width);roles.append(role);layers.append(layer)
  pos=new
 return np.array(paths),np.array(widths),np.array(roles),np.array(layers),xf

def union_footprints(paths,widths,mask):
 # Shapely vectorized buffers use the emitted path's own extrusion width.
 lines=shapely.linestrings(paths[mask]);beads=shapely.buffer(lines,widths[mask]/2,quad_segs=4)
 return shapely.union_all(beads)

def main():
 rows=[];reader=vtk.vtkSTLReader();reader.SetFileName(str(D/'body-mounted.stl'));reader.Update();mesh=reader.GetOutput()
 inside=vtk.vtkSelectEnclosedPoints();inside.Initialize(mesh)
 fig,axes=plt.subplots(2,3,figsize=(13,9),layout='constrained')
 for walls in [8,10]:
  folder=D/'.work'/f'audit-{walls}w'
  if not folder.exists():folder=D/'.work'/f'linux-{walls}w'
  p,w,role,layer,xf=parse(folder)
  settings=json.loads((folder/'effective-settings.json').read_text())
  assert int(settings['wall_loops'])==walls
  for key in ['layer_height','initial_layer_print_height']:assert float(settings[key])==.2
  for key in ['top_shell_layers','bottom_shell_layers']:assert int(settings[key])==6
  assert settings['sparse_infill_density']=='15%'
  assert settings['gap_fill_target']=='everywhere'
  assert settings['wall_generator']=='arachne'
  assert set(layer)==set(range(120)),set(layer)
  roi=box(55,-75,125,22);window=(p[:,:,0].max(1)>54)&(p[:,:,0].min(1)<126)&(p[:,:,1].max(1)>-76)&(p[:,:,1].min(1)<23)
  checks=[]
  # Every one of the 24 intended solid layers, plus the middle of each sparse band.
  targets=[k for k in range(120) if any(a<(k+.5)*.2<b for a,b in PLATE_BANDS)]
  targets+= [19,29,59,89,99]
  for k in targets:
   z=(k+.5)*.2;poly=layer_polygons(mesh,z,inside)
   is_plate=any(a<z<b for a,b in PLATE_BANDS)
   t=.42+(walls-1)*(.45-.2*(1-np.pi/4))
   desired=(poly if is_plate else poly.difference(poly.buffer(-t,quad_segs=8))).intersection(roi)
   select=(layer==k)&window
   if not is_plate:select&=np.isin(role,list(WALL_ROLES))
   footprint=union_footprints(p,w,select)
   # 0.03 mm allowance covers 0.02 mm STL tessellation and 0.001 mm G-code rounding.
   covered=desired.intersection(footprint.buffer(.03)).area/desired.area
   center=poly.intersection(LineString([(90,-75),(90,0)]));spans=list(center.geoms) if hasattr(center,'geoms') else [center]
   span=max(spans,key=lambda x:x.length);a,b=span.bounds[1],span.bounds[3]
   vertical=footprint.buffer(.03).intersection(LineString([(90,a),(90,b)]))
   checks.append({'layer_number':k+1,'z_mid_mm':z,'solid_band':is_plate,'seat_region_nominal_footprint_coverage':covered,'center_X90_extruded_length_mm':vertical.length,'center_X90_envelope_depth_mm':b-a,'extrusion_roles':sorted(set(role[(layer==k)&window]))})
  # Check the full L-plane on one middle layer of each intended solid plate.
  full_planes=[]
  for k in [3,41,79,117]:
   poly=layer_polygons(mesh,(k+.5)*.2,inside)
   footprint=union_footprints(p,w,layer==k)
   full_planes.append({'layer_number':k+1,'coverage_fraction':poly.intersection(footprint.buffer(.03)).area/poly.area})
  finger_checks=[]
  S=np.hypot(100,12);q=np.sqrt(112.4**2-S*S/4);cx=140-12*q/S;cy=6+100*q/S
  for label,c,rot in [('inner',np.array([90,0]),np.arctan2(cy,cx-90)-np.pi/2),('outer',np.array([190,12]),np.arctan2(cy-12,cx-190)-np.pi/2)]:
   sectors=[]
   # Nominal constant-thickness fingers: radii 13..14.35, with rounded
   # noses extending about 2.83 degrees beyond endpoints 161 and 379.
   # The broader CAD-preservation sectors also contain rigid sparse-core
   # arm material, which is not part of the flexible-finger footprint.
   for a,b in [(158,195),(345,382)]:
    theta=np.radians(np.linspace(a,b,200))+rot
    sectors.append(Polygon(np.vstack([c,c+14.5*np.column_stack([np.cos(theta),np.sin(theta)]),c])))
   region=shapely.union_all(sectors)
   local=(p[:,:,0].max(1)>c[0]-20)&(p[:,:,0].min(1)<c[0]+20)&(p[:,:,1].max(1)>c[1]-20)&(p[:,:,1].min(1)<c[1]+20)
   for k in [3,19,41,59,79,99,117]:
    target=layer_polygons(mesh,(k+.5)*.2,inside).intersection(region)
    footprint=union_footprints(p,w,(layer==k)&local&np.isin(role,list(WALL_ROLES)))
    coverage=target.intersection(footprint.buffer(.03)).area/target.area
    finger_checks.append({'seat':label,'layer_number':k+1,'flexible_finger_footprint_coverage':coverage})
    assert coverage>.985,(label,k,coverage)
  summary={'walls':walls,'gcode_sha256':hashlib.sha256((folder/'plate_1.gcode').read_bytes()).hexdigest(),'body_STL_sha256':hashlib.sha256((D/'body-only.stl').read_bytes()).hexdigest(),'slicer':'OrcaSlicer 2.4.2','layer_count':120,'extrusion_segment_count':len(p),'solid_band_layer_count':24,'slice_transform':xf.tolist(),'seat_region_checks':checks,'full_L_plane_checks':full_planes,'minimum_seat_band_coverage':min(c['seat_region_nominal_footprint_coverage'] for c in checks if c['solid_band']),'minimum_seat_wall_coverage':min(c['seat_region_nominal_footprint_coverage'] for c in checks if not c['solid_band'])}
  rows.append(summary);print(json.dumps({k:v for k,v in summary.items() if k not in ['seat_region_checks','slice_transform']},indent=2),flush=True)
  summary['finger_checks']=finger_checks
  summary['wall_generator']=settings['wall_generator']
  summary['gap_fill_target']=settings['gap_fill_target']
  summary['minimum_finger_coverage']=min(c['flexible_finger_footprint_coverage'] for c in finger_checks)
  if walls==8:
   for ax,k in zip(axes.flat,[3,19,41,59,79,117]):
    mask=(layer==k)&window
    colors=np.where(np.isin(role[mask],list(WALL_ROLES)),'#146f78',np.where(role[mask]=='Sparse infill','#bbb9b1','#d38b26'))
    ax.add_collection(LineCollection(p[mask],colors=colors,linewidths=.55))
    ax.set(xlim=(55,125),ylim=(-46,22),aspect='equal',title=f'Layer {k+1} / Z={(k+1)*.2:.1f} mm',xlabel='Projection X (mm)',ylabel='Height Y (mm)')
 fig.suptitle('E13 actual OrcaSlicer paths / inner seat / 8 walls',fontsize=16)
 fig.supxlabel('Teal: walls and gap fill · gold: dense infill / bridge paths · grey: sparse infill (zero structural credit).\nNominal toolpaths, not proof of extrusion quality or bonding.',fontsize=10)
 fig.savefig(D/'toolpath-sections.png',dpi=150);plt.close(fig)
 report={'method':__doc__,'footprint_rounding_allowance_mm':.03,'seat_ROI_mm':[55,-75,125,22],'cases':rows}
 (D/'toolpath-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 for r in rows:
  assert r['minimum_seat_band_coverage']>.985,r
  assert r['minimum_seat_wall_coverage']>.96,r
  assert min(c['coverage_fraction'] for c in r['full_L_plane_checks'])>.985,r
 print('Solid bands and seat-wall footprint checks pass',flush=True)

if __name__=='__main__':main()
