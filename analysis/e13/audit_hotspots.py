"""Matched fine-mesh stress comparison, raw peaks and three-level refinement.

All finite elements are retained, including tiny cells and restraint-edge peaks.
Region percentiles and overstress volumes are diagnostics, not allowables.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from render_fields import grid,plane_slice
D=Path(__file__).resolve().parent

def q(v,w,f=.99):
 i=np.argsort(v);return float(np.interp(f*w.sum(),np.cumsum(w[i]),v[i]))

def read(name):
 r=json.loads((D/f'{name}-results.json').read_text())
 assert r['relative_free_residual']<1e-6 and r['relative_force_balance_error']<1e-6 and r['relative_moment_balance_error']<1e-6
 return r,np.load(D/f'{name}-solution.npz')

def regions(c):
 x,y=c[:,0],c[:,1]
 return {'whole_body':np.ones(len(c),dtype=bool),
 'inner_seat':(x>75)&(x<110)&(y>-24)&(y<0),
 'knee':(x>30)&(x<75)&(y<40),
 'outer_arm':(x>110)&(x<170),
 'upper_landing':(x<10)&(abs(y-164)<9),
 'lower_landing':(x<10)&(abs(y-40)<9)}

def measure(name):
 r,d=read(name);c=d['p'][d['t']].mean(1);out=[]
 mesh=json.loads((D/f'{name}-mesh-quality.json').read_text())
 for label,mask in regions(c).items():
  ids=np.flatnonzero(mask);j=ids[d['vm'][ids].argmax()];v=d['vm'][mask];w=d['volume'][mask]
  out.append({'region':label,'p99_MPa':q(v,w),'p999_MPa':q(v,w,.999),'raw_peak_MPa':float(v.max()),
   'raw_peak_cell_center_mm':c[j].tolist(),'raw_peak_cell_volume_mm3':float(d['volume'][j]),
   'total_region_volume_mm3':float(w.sum()),'volume_above_6MPa_mm3':float(w[v>6].sum()),
   'fraction_above_6MPa':float(w[v>6].sum()/w.sum())})
 return {'mesh':name,'gmsh_3d_algorithm':mesh['gmsh_3d_algorithm'],'nodes':r['nodes'],'tetrahedra':r['tetrahedra'],'front_mm_at_E1000':-r['patches']['front_seat']['mean_displacement_mm_at_E1000'][1],
  'relative_free_residual':r['relative_free_residual'],'solution_sha256':hashlib.sha256((D/f'{name}-solution.npz').read_bytes()).hexdigest(),'regions':out}

def main():
 rows=[];deltas=[];refinement=[]
 for n in [8,10]:
  old=measure(f'baseline-e12-print-material-{n}w-h1');new=measure(f'print-material-{n}w-h1');rows.extend([old,new])
  for a,b in zip(old['regions'],new['regions']):
   deltas.append({'walls':n,'region':a['region'],'E12_p99_MPa':a['p99_MPa'],'E13_p99_MPa':b['p99_MPa'],
    'p99_change_percent':100*(b['p99_MPa']/a['p99_MPa']-1),'E12_raw_peak_MPa':a['raw_peak_MPa'],'E13_raw_peak_MPa':b['raw_peak_MPa'],
    'E12_volume_above_6MPa_mm3':a['volume_above_6MPa_mm3'],'E13_volume_above_6MPa_mm3':b['volume_above_6MPa_mm3']})
  levels=[measure(f'print-material-{n}w-h{h}') for h in ['2','1.5','1']]
  for i,r in enumerate(levels):
   row={'walls':n,'h_mm':[2,1.5,1][i],**r}
   if i:
    previous=levels[i-1];row['front_change_percent']=100*(r['front_mm_at_E1000']/previous['front_mm_at_E1000']-1)
    row['region_p99_changes_percent']={b['region']:100*(b['p99_MPa']/a['p99_MPa']-1) for a,b in zip(previous['regions'],r['regions'])}
   refinement.append(row)
 report={'scope':__doc__,'reference_load_kg_equivalent':12,'matched_comparison_h_mm':1,'comparisons':deltas,'fine_fields':rows,'E13_refinement':refinement,
  'interpretation':'Stable region statistics and movement can be compared; a raw peak that moves or grows on refinement remains unresolved. Small cell volume alone does not prove an artifact. Six MPa is a display/diagnostic threshold, not a material allowable.'}
 (D/'hotspot-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 text='''# E13 hotspot and mesh-refinement audit

E12 and E13 are both solved again at **h=1 mm**, with identical material,
loads, restraints, element formulation and requested mesh sizes. E13 additionally
has h=2 and h=1.5 mm fields. These runs spend resolution on the complete 3D
domain, including seats, chamfers, four plates and screw tunnels.

The 8-wall E12 baseline required the documented HXT retry after Delaunay
boundary recovery failed. The other fine meshes used Delaunay. Thus nominal
resolution is matched, while the meshes and this algorithm choice differ;
raw-peak changes must not be attributed solely to the design.

The long straight underside tapers carry the added depth into adjacent arms.
The physical fingers, small corner finish, bearing surfaces and screw access
remain. No finite elements are removed because of their stress values.

## Matched fine-mesh comparison

| Walls | Region | E12 p99 (MPa) | E13 p99 (MPa) | Change | E12 raw peak (MPa) | E13 raw peak (MPa) |
|---:|---|---:|---:|---:|---:|---:|
'''
 for r in deltas:text+=f"| {r['walls']} | {r['region'].replace('_',' ')} | {r['E12_p99_MPa']:.3f} | {r['E13_p99_MPa']:.3f} | {r['p99_change_percent']:+.2f}% | {r['E12_raw_peak_MPa']:.2f} | {r['E13_raw_peak_MPa']:.2f} |\n"
 text+='''
P99 is volume-weighted within fixed spatial windows, which are identical in
both revisions. The near-seat window excludes the added underside volume;
knee, arm and whole-body windows include material added within those windows.
Raw peaks retain all finite cells. Their coordinates, cell
volumes, p99.9 and material volume above 6 MPa are recorded in
[the complete audit](hotspot-verification.json). Six MPa is a visualization
threshold, not an allowable or a rejection limit.

![Matched fine 3D field details](hotspot-comparison.png)

## Three E13 mesh levels

| Walls | h (mm) | Tetrahedra | Front at E1000 (mm) | Change from previous | Inner-seat p99 (MPa) | Inner-seat p99 change |
|---:|---:|---:|---:|---:|---:|---:|
'''
 for r in refinement:
  seat=next(x for x in r['regions'] if x['region']=='inner_seat')
  change=f"{r['front_change_percent']:+.2f}%" if 'front_change_percent' in r else '—'
  stress=f"{r['region_p99_changes_percent']['inner_seat']:+.2f}%" if 'region_p99_changes_percent' in r else '—'
  text+=f"| {r['walls']} | {r['h_mm']:g} | {r['tetrahedra']:,} | {r['front_mm_at_E1000']:.4f} | {change} | {seat['p99_MPa']:.3f} | {stress} |\n"
 text+='''
Every field passes independent force, moment and free-residual gates below
1e-6. Refinement is a numerical sensitivity study; it does not prove exact
asymptotic convergence, printed anisotropy, contact-pressure distribution or
rupture strength. A raw peak that changes location or magnitude still needs
interpretation. Tiny-cell location alone is insufficient to dismiss it.

The clamped washer/shank transitions, piecewise planar chamfers and ideal
wall-to-plate intersections can retain local peaks. This package does not
claim that all stress concentrations have been eliminated. The retained raw
fields make those limits visible rather than smoothing or clipping them away.
Physical rod fit, snap force, hot loading and lifetime qualification remain
unperformed. [Current material and 3D results](RESULTS.md).

Reproduce the fine E12 baseline using `mesh_model.py print-material 8 1 1
--clean --baseline-e12` followed by `solve3d.py
baseline-e12-print-material-8w-h1 --pardiso`; repeat for 10 walls. The preserved
E12 analysis domains must be built first. Run `audit_hotspots.py` after all
listed E13 refinement fields and both baseline fields are complete.
'''
 (D/'HOTSPOTS.md').write_text(text,encoding='utf-8')
 fig,axes=plt.subplots(2,3,figsize=(13,9),layout='constrained')
 windows=[('Inner seat',(55,122),(-24,18)),('Knee and lower arm',(25,80),(-45,40)),('Lower screw landing',(-.5,15),(27,54))]
 for row,name in enumerate(['baseline-e12-print-material-8w-h1','print-material-8w-h1']):
  g,r=grid(name);v,values=plane_slice(g,(0,0,8.2),(0,0,1))
  for ax,(label,xlim,ylim) in zip(axes[row],windows):
   pc=PolyCollection(v[:,:,(0,1)],array=values,cmap='turbo',norm=Normalize(0,6),edgecolors='none',rasterized=True);ax.add_collection(pc)
   ax.set(xlim=xlim,ylim=ylim,aspect='equal',xlabel='Projection X (mm)',ylabel='Height Y (mm)',title=f"{'E12' if row==0 else 'E13'} / {label}")
 fig.colorbar(pc,ax=axes,shrink=.65,label='Element von Mises stress (MPa)',extend='max')
 fig.suptitle('Matched h=1 mm 3D fields / 8 walls / 12 kg equivalent load',fontsize=16,fontweight='bold')
 fig.supxlabel('Actual tetrahedron intersections at internal plate Z=8.2 mm; common 6 MPa display cap.\nRaw peaks and all finite cells retained in the audit and saved fields. Numerical screening, not physical qualification.',fontsize=10)
 fig.savefig(D/'hotspot-comparison.png',dpi=155);plt.close(fig)
 print(json.dumps({'comparisons':deltas,'refinement':[{'walls':r['walls'],'h':r['h_mm'],'tets':r['tetrahedra'],'front':r['front_mm_at_E1000'],'changes':r.get('region_p99_changes_percent')} for r in refinement]},indent=2),flush=True)

if __name__=='__main__':main()
