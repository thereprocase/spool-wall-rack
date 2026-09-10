"""Checked E12 3D results, current material scaling, and bounded creep cases."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from report_comparison import summary as comparison
D=Path(__file__).resolve().parent

def read(name):
 r=json.loads((D/f'{name}-results.json').read_text())
 for key in ['relative_free_residual','relative_force_balance_error','relative_moment_balance_error']:assert r[key]<1e-6,(name,key)
 return r

def main():
 material=json.loads((D.parents[1]/'designs/closed-wall-e6/material-reference-data.json').read_text())['cases']
 summary={'revision':'E12','status':'Numerical screening and nominal toolpath verification, not physical or lifetime qualification','load_kg_equivalent':12,'E_reference_MPa':1000,'nu':.35,'sparse_infill_structural_credit':0,'serviceability':{'total_loaded_movement_mm':5,'one_roll_change_mm':1,'roll_gross_kg':1.25},'cases':[],'mesh_checks':[],'peak_diagnostics':[],'comparison_2d':comparison}
 for label,n in [('PLA',8),('PETG',10),('ASA',8),('PA6-GF dry',8),('PA6-GF wet',8)]:
  m=next(x for x in material if x['case']==label);name=f'print-material-{n}w-h2';r=read(name)
  K=-1000*r['patches']['front_seat']['mean_displacement_mm_at_E1000'][1];Kr=-1000*r['patches']['rear_seat']['mean_displacement_mm_at_E1000'][1];E=m['young_modulus_XY_MPa'];delta=K/E
  summary['cases'].append({'material':label,'reference_grade':m['reference_grade'],'walls':n,'source_mesh':name,'reference_E_MPa':E,'front_K_MPa_mm':K,'rear_K_MPa_mm':Kr,'initial_front_mm':delta,'one_roll_initial_mm':delta*1.25/12,'minimum_creep_modulus_MPa_for_5mm_bracket_only':K/5,'compliance_multiplier_limit_bracket_only':5/delta,'linear_24kg_front_mm':2*delta,'source_url':m['source_url'],'source_sha256':m['source_sha256']})
 for n in [8,10]:
  coarse_h=3 if n==8 else 2.5
  a=read(f'print-material-{n}w-h{coarse_h}');b=read(f'print-material-{n}w-h2')
  da=-a['patches']['front_seat']['mean_displacement_mm_at_E1000'][1];db=-b['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
  sa=a['regions']['near_rear_seat_fixed_window']['vm_p99_MPa'];sb=b['regions']['near_rear_seat_fixed_window']['vm_p99_MPa']
  plane=json.loads((D/f'e12-{n}w-h1-full-results.json').read_text())
  summary['mesh_checks'].append({'walls':n,'coarse_h_mm':coarse_h,'fine_h_mm':2,'coarse_tets':a['tetrahedra'],'fine_tets':b['tetrahedra'],'coarse_front_mm_at_E1000':da,'fine_front_mm_at_E1000':db,'front_movement_change_percent':100*(db/da-1),'near_seat_p99_coarse_MPa':sa,'near_seat_p99_fine_MPa':sb,'near_seat_p99_change_percent':100*(sb/sa-1),'raw_peak_coarse_MPa':a['vm_max_MPa_not_allowable'],'raw_peak_fine_MPa':b['vm_max_MPa_not_allowable'],'fine_residual':b['relative_free_residual'],'twoD_front_vs_threeD_percent':100*((-plane['patches']['front_seat']['mean_displacement_mm_at_E1000'][1])/db-1),'upper_washer_outward_N':-b['head_164_reaction_N'][0],'lower_washer_outward_N':-b['head_40_reaction_N'][0],'linear_24kg_near_seat_p99_MPa':2*sb,'linear_24kg_front_mm_at_E1000':2*db})
  for h in [coarse_h,2]:
   name=f'print-material-{n}w-h{h}';d=np.load(D/f'{name}-solution.npz');i=int(d['vm'].argmax())
   summary['peak_diagnostics'].append({'mesh':name,'raw_vm_peak_MPa':float(d['vm'][i]),'cell_center_mm':d['p'][d['t'][i]].mean(0).tolist(),'cell_volume_mm3':float(d['volume'][i]),'solution_sha256':hashlib.sha256((D/f'{name}-solution.npz').read_bytes()).hexdigest()})
 a=read('landing-8w-h1');b=read('landing-8w-h0.65');da=a['patches']['washer']['mean_displacement_mm_at_E1000'][0];db=b['patches']['washer']['mean_displacement_mm_at_E1000'][0]
 summary['landing_fine']=b;summary['landing_refinement']={'coarse_tets':a['tetrahedra'],'fine_tets':b['tetrahedra'],'movement_change_percent':100*(db/da-1),'fine_washer_movement_mm_at_E1000':-db,'fine_raw_VM_MPa':b['vm_max_MPa_not_allowable']}
 tau=np.array([1,10,100,1000,10000,100000.]);A=np.array([.005,.010,.015,.010,.020,.080])
 def G(t):return 1+np.sum(A*(1-np.exp(-np.asarray(t)[...,None]/tau)),axis=-1)
 summary['published_PETG_example']={'source':'https://doi.org/10.3390/polym17152075','tau_seconds':tau.tolist(),'A_dimensionless':A.tolist(),'transcription':'Approximate Figure 26 bar heights from the retained reference study','G_5h':float(G(5*3600)),'G_20h':float(G(20*3600)),'formal_plateau':float(1+A.sum()),'scope':'Devil Design, unidirectional 100% specimens, 21.3 C; tests to 20 h. Not a bracket-grade or service-temperature lifetime law.'}
 summary['planning_scenarios']=[]
 for year in [1,5,10]:
  for tail in [0,.02,.10]:
   row={'years':year,'assumed_unmeasured_compliance_tail_per_year':tail,'G':float(G(year*365*86400)+tail*year)}
   for c in summary['cases']:row[c['material']+'_front_mm']=row['G']*c['initial_front_mm']
   summary['planning_scenarios'].append(row)
 summary['thermal_shift_scenarios']=[];R=8.314462618;Tref=273.15+(85-32)*5/9;Thot=273.15+(100-32)*5/9
 for Q in [50,100,200]:
  rate=np.exp(Q*1000/R*(1/Tref-1/Thot));summary['thermal_shift_scenarios'].append({'assumed_activation_kJ_mol':Q,'hot_rate_factor':float(rate),'equivalent_hours_per_year':float(8754+6*rate),'extra_time_percent':float(100*6*(rate-1)/8760)})
 summary['numerical_rejections']=[{'case':'Initial 10-wall h3 HXT mesh','reason':'Independent free residual 2.187638e-4 exceeded 1e-6; field rejected. Surface-algorithm-5 retry crashed during HXT generation. Accepted 10-wall meshes use h2.5 and h2, surface algorithm 6 and Delaunay 3D, on the unchanged cleaned analysis domain.'}]
 summary['mesh_audits']={f.stem:json.loads(f.read_text()) for f in D.glob('*-mesh-quality.json')}
 summary['source_geometry']=[json.loads((D/f'geometry-{n}w.json').read_text()) for n in [8,10]]
 fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');hours=np.geomspace(.001,20,240)
 axes[0].semilogx(hours,G(hours*3600),color='#187d83',lw=2);axes[0].set(xlabel='Hours',ylabel='Normalized compliance J / J0',title='Published PETG example / tested time window')
 years=np.linspace(0,10,300)
 for tail in [0,.02,.10]:axes[1].plot(years,G(years*365*86400)+tail*years,label=f'Assumed tail {tail:.2f} / year')
 axes[1].set(xlabel='Years',ylabel='Normalized compliance J / J0',title='Unmeasured continuation / sensitivity only');axes[1].legend()
 for ax in axes:ax.grid(alpha=.2)
 fig.suptitle('E12 material planning / creep evidence and its limits',fontsize=15)
 fig.supxlabel('A finite fitted spectrum plateaus by construction. These curves are not service-life predictions.\nE12 movement scenarios use the newly solved E12 geometry coefficients.',fontsize=9)
 fig.savefig(D/'creep-sensitivity.png',dpi=155);plt.close(fig)
 (D/'engineering-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 text='''# E12 solved engineering results

The reinforced inner seat and mirrored 50° finish have been re-solved in 2D and
3D. The printable body stays solid CAD with two separate modifier helpers; only
the analysis domains remove sparse core material.

## Quarter-depth tradeoff

E12 reduces added depth from **38 to 9.5 mm**, meeting the one-quarter target
and one-third maximum. The broader smooth blend retains the fingers, R6 rigid
shoulders, continuous plates and mirrored 50° chamfers. No relief holes were
needed for the measured improvement.

The matched reduced model gives **31.7–32.5% lower near-seat stress than E10**,
versus E11's 37.4–37.6%. Movement is 5.6–7.1% higher than E11, while the added
protrusion is 75% smaller. The outer-rod-only statistic improves about 35% over
E10. [All three revisions, exact values and mesh checks](COMPARISON.md).

The local finished section improves over E10 but no longer exceeds both
adjacent plain-arm bands. This is the explicit tradeoff from the new depth
cap; the adjacent arms were not weakened to manufacture a favorable ratio.
[Section audit](../../designs/closed-wall-e12/section-verification.json).

## Current 3D solution and refinement

12 kg equivalent per bracket; E = 1,000 MPa and ν = 0.35. The near-seat window is
X = 75–110 mm, Y = −24–0 mm, over the full width.

| Walls | Tetrahedra, coarse → fine | Front movement at E1000 (mm) | Movement change | Near-seat p99, coarse → fine (MPa) | p99 change |
|---:|---:|---:|---:|---:|---:|
'''
 for c in summary['mesh_checks']:text+=f"| {c['walls']} | {c['coarse_tets']:,} → {c['fine_tets']:,} | {c['fine_front_mm_at_E1000']:.3f} | {c['front_movement_change_percent']:.2f}% | {c['near_seat_p99_coarse_MPa']:.2f} → {c['near_seat_p99_fine_MPa']:.2f} | {c['near_seat_p99_change_percent']:.2f}% |\n"
 text+='''
![8-wall 3D stress and cutaway](fem-3d.png)

![Cuts through the actual solved tetrahedra](fem-sections.png)

[10-wall 3D view](fem-3d-10w.png). The 6 MPa colour cap makes the working field
visible; saved fields retain every solved value. Percentiles and raw peaks are
not stress allowables. These meshes do not establish asymptotic convergence,
printed orthotropy, layer adhesion, snap insertion, rupture or lifetime strength.

| Walls | Raw peak, coarse (MPa) | Raw peak, fine (MPa) | Fine free residual | 2D front coefficient relative to 3D |
|---:|---:|---:|---:|---:|
'''
 for c in summary['mesh_checks']:text+=f"| {c['walls']} | {c['raw_peak_coarse_MPa']:.1f} | {c['raw_peak_fine_MPa']:.1f} | {c['fine_residual']:.2e} | {c['twoD_front_vs_threeD_percent']:+.2f}% |\n"
 text+='''
Raw peaks remain sensitive to small cells at chamfer, tunnel and analysis-core
intersections. Their locations and volumes are in `engineering-summary.json`.
All published 3D fields pass independently recomputed free residual, force and
moment balance below 1e-6. The affine test checks displacement, recovered stress
and strain energy; PARDISO agrees with an independent SuperLU patch solution.
The reduced solver has separate affine and beam checks.

All four global domains use audited same-domain CAD face cleanup. The initial
10-wall h3 HXT field failed the residual gate (2.19e-4); it was rejected. A
surface-mesher retry crashed before producing an accepted field. The accepted
10-wall pair uses h2.5/h2 Delaunay meshes on the same geometry. The 8-wall pair
uses h3/h2. No finite cells were deleted for their stress values.
`analysis-topology-cleanup.json` and mesh audits record volumes and any
numerically zero-volume removal. Saved fields retain raw peaks.

## Material movement and creep margin

The retained grade-specific room-temperature XY moduli are applied to E12's new
coefficients. They are not measured hot or aged properties.

| Material | Walls | E (MPa) | K (MPa·mm) | Initial front (mm) | One 1.25 kg roll (mm) | Ec for 5 mm bracket-only (MPa) | Compliance growth limit |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
 for c in summary['cases']:text+=f"| {c['material']} | {c['walls']} | {c['reference_E_MPa']:.0f} | {c['front_K_MPa_mm']:.1f} | {c['initial_front_mm']:.3f} | {c['one_roll_initial_mm']:.3f} | {c['minimum_creep_modulus_MPa_for_5mm_bracket_only']:.0f} | {c['compliance_multiplier_limit_bracket_only']:.2f}× |\n"
 text+='''
`δ(t,T) = K × J(t,T) = K / Ec(t,T)` assumes common linear-viscoelastic compliance
and an unchanged load/contact state. For the whole rack use **Ec ≥ K / (5 mm −
dowel movement − wall/fastener movement)**. Retain the project screening target
of at least 1.0 GPa effective creep modulus at the intended age and loaded
temperature history; it is not a published allowable or rupture criterion.

The one-roll calculation assigns its entire reaction to one bracket for the
stated simple/two-equal-span case. Fast unloading uses aged instantaneous
modulus, not reversal of accumulated creep. Other support arrangements,
overhangs and impact need their actual reactions.

PLA/PETG remain prototype choices; ASA is the higher-temperature comparison.
PA6-GF dry and water-conditioned cases stay separate. Match the source's
100°C/16-hour annealing and conditioning before using its properties, and
recheck fit. [Exact grades, source URLs and hashes](../../designs/closed-wall-e6/material-reference-data.json).

## 24 kg brief proof scenario

Elastic stress and movement double at 24 kg with the same load pattern and
active contact. This is linear scaling, not a damage simulation or a performed
physical proof test.

| Walls | Near-seat p99 at 24 kg (MPa) | Front movement at E1000 (mm) |
|---:|---:|---:|
'''
 for c in summary['mesh_checks']:text+=f"| {c['walls']} | {c['linear_24kg_near_seat_p99_MPa']:.2f} | {c['linear_24kg_front_mm_at_E1000']:.3f} |\n"
 text+='''
## Screw landings and contact

The global model uses compression-only wall contact, rigid washer axial
restraints and rigid shank shear restraints. No tightening friction or arbitrary
preload is credited. The lower washer carries substantial outward demand.

| Walls | Upper washer outward demand (N) | Lower washer outward demand (N) |
|---:|---:|---:|
'''
 for c in summary['mesh_checks']:text+=f"| {c['walls']} | {c['upper_washer_outward_N']:.1f} | {c['lower_washer_outward_N']:.1f} |\n"
 c=summary['landing_refinement'];text+=f"\nThe separate **500 N upper-landing submodel** uses the actual 3.6 mm land and flat rear support. Its {c['coarse_tets']:,} → {c['fine_tets']:,} tetrahedron refinement changes washer movement by {c['movement_change_percent']:.2f}%. Fine mean movement is **{c['fine_washer_movement_mm_at_E1000']:.5f} mm at E1000**, with a **{c['fine_raw_VM_MPa']:.2f} MPa** raw peak. This constant-force scenario does not predict installed clamp-force retention.\n"
 text+='''
![E12 screw-landing stress](fem-landing.png)

Retain the backed 3.6 mm land. A gap behind it creates bending/punching conditions
outside this submodel. Use the checked washer dimensions and substrate-appropriate
fixings. Separate scalar von Mises maxima from service and tightening cannot be
added as if they were stress tensors.

## Creep sensitivity with E12 coefficients

The retained [PETG study](https://doi.org/10.3390/polym17152075) supplies a short-time
example at about 21.3°C, tested to 20 hours. Its approximate Figure 26 spectrum
gives compliance multipliers near 1.07 at five hours and 1.10 at twenty hours.
The formal 1.14 plateau is built into the finite fit and does not prove years of
behavior at 85°F for these bracket grades.

![Short-time evidence and unmeasured tails](creep-sensitivity.png)

These deliberately different long-time tails use E12's new movement coefficients.
They are **not PLA/PETG service-life forecasts**.

| Years | Assumed extra compliance / year | Multiplier | PLA front (mm) | PETG front (mm) |
|---:|---:|---:|---:|---:|
'''
 for c in summary['planning_scenarios']:text+=f"| {c['years']} | {c['assumed_unmeasured_compliance_tail_per_year']:.2f} | {c['G']:.2f} | {c['PLA_front_mm']:.2f} | {c['PETG_front_mm']:.2f} |\n"
 text+='''
At 85°F sustained and 100°F for six loaded hours/year, the uncalibrated Arrhenius
sensitivity assumes 50/100/200 kJ/mol activation energy. Hot-rate factors are
1.70/2.90/8.42, adding 0.048%/0.130%/0.508% to annual equivalent time. This does
not prove thermal adequacy; actual hot softening, nonlinear creep and rupture
remain unqualified. Full numerical values are in `engineering-summary.json`.

## Print evidence and qualification boundary

The delivered STEP contains one valid body and two aligned helpers. Both faces
measure 50°. Complete flexible-finger sectors match E10 at nine print depths;
hardware and nominal spool-clearance checks pass. Actual OrcaSlicer 8/10-wall
G-code verifies the four solid bands and seat-wall footprints.
[CAD and toolpath evidence](../../designs/closed-wall-e12/README.md).

The 5 mm total loaded-movement and 1 mm per-roll-change limits include dowels and
mounts. Rod fit, snap behavior, extrusion quality, sustained/hot movement and
creep rupture still need physical qualification. No lifetime safe spool count
is assigned by this revision.

[Reproduce](README.md) · [Current print and engineering guide](../../README.md).
'''
 (D/'RESULTS.md').write_text(text,encoding='utf-8')
 print(json.dumps({'cases':summary['cases'],'mesh_checks':summary['mesh_checks'],'landing':summary['landing_refinement']},indent=2))

if __name__=='__main__':main()
