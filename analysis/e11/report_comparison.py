"""Report the matched E10/E11 reduced FEM comparisons, including mesh checks."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
D=Path(__file__).resolve().parent

def read(revision,walls,h=1,load='full'):
 return json.loads((D/f'{revision}-{walls}w-h{h}-{load}-results.json').read_text())

rows=[];checks=[]
for walls in [8,10]:
 a=read('e10',walls);b=read('e11',walls)
 sa=a['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa']
 sb=b['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa']
 da=-a['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
 db=-b['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
 rows.append({'walls':walls,'E10_near_seat_p99_MPa':sa,'E11_near_seat_p99_MPa':sb,
  'stress_reduction_percent':100*(1-sb/sa),'E10_front_mm_at_E1000':da,
  'E11_front_mm_at_E1000':db,'front_movement_reduction_percent':100*(1-db/da)})
 for revision in ['e10','e11']:
  coarse=read(revision,walls,2);fine=read(revision,walls,1)
  assert fine['relative_free_residual']<1e-6 and coarse['relative_free_residual']<1e-6
  pa=coarse['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa']
  pb=fine['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa']
  ua=coarse['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
  ub=fine['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
  checks.append({'revision':revision.upper(),'walls':walls,'coarse_triangles':coarse['triangles'],
   'fine_triangles':fine['triangles'],'rear_p99_change_percent':100*(pb/pa-1),
   'front_movement_change_percent':100*(ub/ua-1),'fine_residual':fine['relative_free_residual']})
outer=[read(r,8,1,'outer_only') for r in ['e10','e11']]
op=[r['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa'] for r in outer]
summary={'status':'Matched reduced-model numerical screening, not physical or lifetime qualification',
 'full_load_comparison':rows,'refinement_checks':checks,
 'outer_rod_only':{'rear_applied_force_N':outer[0]['patches']['rear_seat']['force_N'],
  'front_applied_force_N':outer[0]['patches']['front_seat']['force_N'],
  'E10_near_seat_p99_MPa':op[0],'E11_near_seat_p99_MPa':op[1],
  'reduction_percent':100*(1-op[1]/op[0])}}
(D/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n')

fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
for col,revision in enumerate(['e10','e11']):
 for row,load in enumerate(['full','outer_only']):
  data=np.load(D/f'{revision}-8w-h1-{load}-solution.npz');p=data['p'];t=data['t']
  ax=axes[row,col];tri=Triangulation(p[:,0],p[:,1],t)
  artist=ax.tripcolor(tri,facecolors=data['vm'],cmap='turbo',vmin=0,vmax=7.5,rasterized=True)
  ax.set(xlim=(40,140),ylim=(-76,24),aspect='equal',xlabel='Projection X (mm)',ylabel='Height Y (mm)',
   title=f"{revision.upper()} / {'full load' if load=='full' else 'outer rod only'}")
fig.colorbar(artist,ax=axes,label='Projected-model von Mises stress (MPa)',shrink=.8)
fig.suptitle('E11 / inner-seat stress comparison · 8 walls · identical colour scale')
fig.savefig(D/'seat-stress-comparison.png',dpi=150)

text='''# E11 comparative stress screen

The reinforced inner seat is compared with the actual E10 finish using the
same plane-stress solver, contact assumptions and 12 kg equivalent bracket
load. The 120 layer-midpoint material sections include the finished chamfers,
ideal contour walls and four 1.2 mm solid plates. Sparse infill receives zero
credit. The E11 3D analysis and material scaling are in RESULTS.md.

| Walls | E10 near-seat p99 (MPa) | E11 near-seat p99 (MPa) | Reduction | Front movement reduction |
|---:|---:|---:|---:|---:|
'''
for r in rows:text+=f"| {r['walls']} | {r['E10_near_seat_p99_MPa']:.2f} | {r['E11_near_seat_p99_MPa']:.2f} | {r['stress_reduction_percent']:.1f}% | {r['front_movement_reduction_percent']:.1f}% |\n"
text+='''
The stress statistic uses the same fixed window, X=75–110 mm and Y=−24–0 mm,
in both designs. Added underside volume is not included in that percentile
denominator. Raw maxima and wider-region results remain in each result JSON.
These are stress-field summaries, not rupture allowables.

![Matched inner-seat stress fields](seat-stress-comparison.png)

## Outer-rod-only diagnostic

'''
text+=f"With no load applied at the inner seat, E10 still develops a near-seat p99 of **{op[0]:.2f} MPa**. E11 reduces that to **{op[1]:.2f} MPa**, a **{100*(1-op[1]/op[0]):.1f}%** reduction. This supports the reduced-section bending diagnosis; it does not imply that real bearing/contact effects are absent.\n"
text+='''
## Numerical checks and limits

All reported cases pass independent force/moment balance and free-residual
checks below 1e-6. The affine/beam solver checks are recorded separately.

| Revision | Walls | Triangles, coarse → fine | Rear p99 change | Front movement change |
|---|---:|---:|---:|---:|
'''
for r in checks:text+=f"| {r['revision']} | {r['walls']} | {r['coarse_triangles']:,} → {r['fine_triangles']:,} | {r['rear_p99_change_percent']:.2f}% | {r['front_movement_change_percent']:.2f}% |\n"
text+='''
Two meshes provide a sensitivity check, not proof of asymptotic convergence.
The model averages stress across the printed width and projects the fixing
restraints onto the wall. It cannot resolve 3D bearing stress, layer adhesion,
FFF orthotropy, snap insertion, wall compliance or long-term creep. Do not
use these reductions to increase an allowed spool count without qualification.

The section-property checks in `designs/closed-wall-e11/section-verification.json`
separately demonstrate the required stiffness and elastic section-modulus
margins over both adjacent plain-arm reference bands.

## Reproduce

Use the pinned CAD/FEM packages in `requirements.txt`; build and verify the E10
and E11 STLs first. Run `python verify_solver.py`, `python solve_comparison.py`,
then `python report_comparison.py`. Set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1.
Layer-outline caches under `.work/` are keyed to the finished STL SHA-256.
'''
(D/'COMPARISON.md').write_text(text,encoding='utf-8')
print(json.dumps(summary,indent=2))
