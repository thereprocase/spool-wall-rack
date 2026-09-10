"""Matched E10/E11/E12 comparison from the actual solved reduced fields."""
from pathlib import Path
import hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
D=Path(__file__).resolve().parent

def folder(rev):return D if rev=='e12' else D.parent/'e11'
def read(rev,n,h,case='full'):
 path=folder(rev)/f'{rev}-{n}w-h{h}-{case}-results.json';r=json.loads(path.read_text())
 assert r['relative_free_residual']<1e-6
 assert np.linalg.norm(np.array(r['applied_force_N'])+np.array(r['reaction_N']))<1e-5
 assert abs(r['applied_moment_Nmm']+r['reaction_moment_Nmm'])<1e-3
 return r
rows=[];deltas=[]
for n in [8,10]:
 local=[]
 for rev in ['e10','e11','e12']:
  a=read(rev,n,2);b=read(rev,n,1)
  sa=a['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa'];sb=b['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa']
  da=-a['patches']['front_seat']['mean_displacement_mm_at_E1000'][1];db=-b['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
  row={'revision':rev.upper(),'walls':n,'near_seat_p99_MPa':sb,'front_mm_at_E1000':db,'coarse_to_fine_stress_percent':100*(sb/sa-1),'coarse_to_fine_movement_percent':100*(db/da-1),'fine_residual':b['relative_free_residual']}
  rows.append(row);local.append(row)
 old,deep,slim=local
 deltas.append({'walls':n,'E12_stress_reduction_vs_E10_percent':100*(1-slim['near_seat_p99_MPa']/old['near_seat_p99_MPa']),'E12_movement_reduction_vs_E10_percent':100*(1-slim['front_mm_at_E1000']/old['front_mm_at_E1000']),'E12_stress_increase_vs_E11_percent':100*(slim['near_seat_p99_MPa']/deep['near_seat_p99_MPa']-1),'E12_movement_increase_vs_E11_percent':100*(slim['front_mm_at_E1000']/deep['front_mm_at_E1000']-1)})
outer=[]
for rev in ['e10','e11','e12']:
 r=read(rev,8,1,'outer_only');outer.append({'revision':rev.upper(),'near_seat_p99_MPa':r['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa'],'front_mm_at_E1000':-r['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]})
summary={'cases':rows,'E12_comparisons':deltas,'outer_only_8wall':outer,'E12_outer_only_stress_reduction_vs_E10_percent':100*(1-outer[2]['near_seat_p99_MPa']/outer[0]['near_seat_p99_MPa']),'scope':'Matched ideal printed-material plane stress; actual 120-layer finished STL outlines. Same loads and restraints, zero sparse-infill credit. Near-seat volume-weighted p99 uses fixed X75..110,Y-24..0.'}
(D/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
fig,axes=plt.subplots(1,3,figsize=(13,7),layout='constrained')
for ax,rev in zip(axes,['e10','e11','e12']):
 f=folder(rev)/f'{rev}-8w-h1-full-solution.npz';d=np.load(f)
 t=Triangulation(d['p'][:,0],d['p'][:,1],d['t']);art=ax.tripcolor(t,facecolors=d['vm'],cmap='turbo',vmin=0,vmax=6.5,rasterized=True)
 r=next(x for x in rows if x['revision']==rev.upper() and x['walls']==8)
 ax.set(xlim=(55,127),ylim=(-75,22),aspect='equal',xlabel='Projection X (mm)',title=f"{rev.upper()} / added depth {dict(e10=0,e11=38,e12=9.5)[rev]:g} mm\nNear-seat p99 {r['near_seat_p99_MPa']:.2f} MPa")
 ax.set_ylabel('Height Y (mm)')
fig.colorbar(art,ax=axes,shrink=.7,label='Element von Mises stress (MPa)',extend='max')
fig.suptitle('E12 / quarter-depth tradeoff / matched 8-wall solved fields',fontsize=16,fontweight='bold')
fig.supxlabel('Identical 12 kg load and contour-wall/plate assumptions · fixed statistic window · display capped at 6.5 MPa · numerical screening',fontsize=10)
fig.savefig(D/'seat-stress-comparison.png',dpi=150);plt.close(fig)
text='''# E12 matched comparison with E10 and E11

E12 uses **9.5 mm added depth**, one-quarter of E11's 38 mm, with a broader
smooth blend. It retains the 50° finish, R6 rigid shoulder treatment, fingers,
rail centers and hardware. No strain-relief holes were added: the shallow
continuous section already retains most of the measured E11 benefit.

The new depth cap supersedes the earlier demand that the inner-seat section
exceed both adjacent arms. The adjacent-section ratios are reported openly in
[the section audit](../../designs/closed-wall-e12/section-verification.json).

| Revision | Walls | Near-seat p99 (MPa) | Front movement at E1000 (mm) | Stress refinement change | Movement refinement change |
|---|---:|---:|---:|---:|---:|
'''
for r in rows:text+=f"| {r['revision']} | {r['walls']} | {r['near_seat_p99_MPa']:.3f} | {r['front_mm_at_E1000']:.3f} | {r['coarse_to_fine_stress_percent']:+.2f}% | {r['coarse_to_fine_movement_percent']:+.2f}% |\n"
text+='\n| Walls | Stress reduction vs E10 | Movement reduction vs E10 | Stress increase vs E11 | Movement increase vs E11 |\n|---:|---:|---:|---:|---:|\n'
for r in deltas:text+=f"| {r['walls']} | {r['E12_stress_reduction_vs_E10_percent']:.2f}% | {r['E12_movement_reduction_vs_E10_percent']:.2f}% | {r['E12_stress_increase_vs_E11_percent']:.2f}% | {r['E12_movement_increase_vs_E11_percent']:.2f}% |\n"
text+='\n![Actual matched stress fields](seat-stress-comparison.png)\n\n## Outer rod only\n\n| Revision | Near-seat p99 (MPa) | Front movement at E1000 (mm) |\n|---|---:|---:|\n'
for r in outer:text+=f"| {r['revision']} | {r['near_seat_p99_MPa']:.3f} | {r['front_mm_at_E1000']:.3f} |\n"
text+=f"\nE12 reduces this outer-only near-seat statistic by **{summary['E12_outer_only_stress_reduction_vs_E10_percent']:.2f}%** relative to E10.\n"
text+='''
## Scope and reproduction

All cases use the same finished-layer integration, plane-stress law, load
patches and projected fixing/contact assumptions. The volume-weighted p99
window is fixed at X=75–110 mm, Y=−24–0 mm, excluding the added underside
volume from its denominator. Refinement uses h=2 and h=1 mm; these changes are
numerical sensitivity, not asymptotic convergence or independent validation.

The E10/E11 fields are retained in [the E11 package](../e11/README.md); only E12
was newly solved here. Every referenced field passes independent residual,
force and moment checks. The affine/beam verification is separate from these
bracket solves. Run `solve_comparison.py e12 8 1` (and the other documented
wall/mesh/load cases), then `report_comparison.py` to regenerate this report.

Stress percentiles are comparison metrics, not rupture allowables. The model
does not establish layer adhesion, snap insertion force, actual rod contact,
creep or a safe spool count. [Current 3D/material results](RESULTS.md).
'''
(D/'COMPARISON.md').write_text(text,encoding='utf-8')
if __name__=='__main__':print(json.dumps(summary,indent=2))
