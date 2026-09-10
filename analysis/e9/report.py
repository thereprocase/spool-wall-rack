"""Render actual solved FEM fields and calculate explicitly conditional creep margins."""
from pathlib import Path
import json,itertools
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skfem import MeshTet
D=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.facecolor':'#f7f7f3','axes.facecolor':'#f7f7f3'})
def read(name):return json.loads((D/f'{name}-results.json').read_text())
def best(n):
 fine=f'print-material-{n}w-h2'
 return fine if (D/f'{fine}-results.json').exists() else f'print-material-{n}w-h3'
def render2(name):
 d=np.load(D/f'{name}-solution.npz');p=d['p'];t=d['t']
 fig,ax=plt.subplots(1,2,figsize=(12,7),layout='constrained')
 for a,val,title,cap in [(ax[0],d['vm'],'2D FEM: von Mises stress',8),(ax[1],d['thickness'],'Effective solid thickness',24)]:
  c=PolyCollection(p[t],array=val,cmap='turbo' if cap==8 else 'viridis',norm=Normalize(0,cap),edgecolors='none',antialiased=False);a.add_collection(c);a.autoscale();a.set_aspect('equal');a.set_xlabel('Projection from wall (mm)');a.set_ylabel('Installed height (mm)');a.set_title(title);fig.colorbar(c,ax=a,shrink=.75,label='MPa' if cap==8 else 'mm')
 fig.suptitle('E9 front rail +12 mm • 8 walls • 12 kg equivalent per bracket',fontsize=16,fontweight='bold')
 fig.supxlabel('Plane stress with integrated print thickness; no sparse-infill credit.\nChamfers omitted; mounting restraints projected onto wall. Stress scale capped at 8 MPa.',fontsize=9)
 fig.savefig(D/'fem-2d.png',dpi=160);plt.close(fig)
def render3(name,output,landing=False):
 d=np.load(D/f'{name}-solution.npz');p=d['p'];t=d['t'];m=MeshTet(p.T,t.T);bf=m.boundary_facets();faces=m.facets[:,bf].T;values=d['vm'][m.f2t[0,bf]];xyz=p[:,[0,2,1]]
 fig=plt.figure(figsize=(12,8),layout='constrained');ax=fig.add_subplot(111,projection='3d');cap=6 if landing else 8;norm=Normalize(0,cap);cmap=plt.get_cmap('turbo')
 c=Poly3DCollection(xyz[faces],facecolors=cmap(norm(values)),edgecolors='none',antialiased=False,rasterized=True);ax.add_collection3d(c);lo=xyz.min(0);hi=xyz.max(0)
 ax.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),zlim=(lo[2],hi[2]));ax.set_box_aspect(hi-lo);ax.view_init(elev=20,azim=-35 if landing else -60)
 ax.set_xlabel('Projection X (mm)',labelpad=2 if landing else 10);ax.set_ylabel('Width (mm)',labelpad=12);ax.set_zlabel('Height Y (mm)',labelpad=10);ax.set_yticks([0,12,24])
 fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=ax,shrink=.65,pad=.04,label='Element von Mises stress (MPa)')
 fig.suptitle('3D landing FEM • 500 N washer compression' if landing else f'E9 3D FEM • {name.split("-")[2]} • 12 kg equivalent load',fontsize=17,fontweight='bold')
 fig.supxlabel('Actual 3.6 mm land with flat rear support; nominal Ø13 / Ø5.5 washer patch.\nConstant force scenario; installed preload can relax.' if landing else 'Actual chamfered exterior, ideal contour walls and four 1.2 mm plates; sparse infill removed.\nCompression-only wall; rigid washer and shank restraints. Undeformed geometry. Peaks are not allowables.',fontsize=9)
 fig.savefig(D/output,dpi=160);plt.close(fig)
def raised_front():
 out=[]
 for dia in [180,200,220]:
  for h in [0,12]:
   R=dia/2+12.7;L=100;S=np.hypot(L,h);q=np.sqrt(R*R-S*S/4);x=140-h*q/S;y=h/2+L*q/S;a=x-90;b=190-x;den=a*(y-h)+b*y
   out.append({'spool_diameter_mm':dia,'front_rise_mm':h,'center_x_mm':x,'center_y_mm':y,'rear_vertical_fraction':b*y/den,'front_vertical_fraction':a*(y-h)/den,'outward_each_over_weight':a*b/den,'wall_moment_at_12kg_Nm':117.72*x/1000,'moment_about_rear_rail_Nm':117.72*a/1000})
 fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
 for ax,h in zip(axes,[0,12]):
  row=next(r for r in out if r['spool_diameter_mm']==200 and r['front_rise_mm']==h)
  for x,y in [(90,0),(190,h)]:ax.add_patch(plt.Circle((x,y),12.7,color='#b78d54'))
  ax.add_patch(plt.Circle((row['center_x_mm'],row['center_y_mm']),100,facecolor='#d9e4e7',edgecolor='#526b76',alpha=.65));ax.plot([0,0],[-35,220],color='#455057',lw=4)
  ax.annotate('Weight',xy=(row['center_x_mm'],row['center_y_mm']-40),xytext=(row['center_x_mm'],row['center_y_mm']+10),arrowprops={'arrowstyle':'->','lw':2})
  ax.set(xlim=(-10,250),ylim=(-35,220),aspect='equal',xlabel='Distance from wall (mm)',ylabel='Height (mm)',title=f'Front rail +{h} mm')
  ax.text(12,195,f'Center: {row["center_x_mm"]:.1f} mm from wall\nRear/front: {100*row["rear_vertical_fraction"]:.1f}% / {100*row["front_vertical_fraction"]:.1f}%\nWall moment: {row["wall_moment_at_12kg_Nm"]:.2f} N·m',fontsize=10)
 fig.suptitle('Raised-front statics study • 200 mm spool • 25.4 mm dowels',fontsize=16,fontweight='bold')
 fig.supxlabel('Two frictionless contacts. E9 implements the raised front rail and a reshaped back arm; this chart isolates the rail statics.',fontsize=9)
 fig.savefig(D/'raised-front-statics.png',dpi=160);plt.close(fig)
 return out
def main():
 material=json.loads((D.parents[1]/'designs/closed-wall-e6/material-reference-data.json').read_text())['cases']
 rows=[];summary={'status':'Numerical screening, not physical validation or a creep-rupture rating','serviceability':{'total_loaded_movement_limit_mm':5,'one_roll_change_limit_mm':1,'roll_gross_kg':1.25,'bracket_target_kg':12},'cases':[],'mesh_checks':[]}
 for label,n in [('PLA',8),('PETG',10),('ASA',8),('PA6-GF dry',8),('PA6-GF wet',8)]:
  m=next(x for x in material if x['case']==label);name=best(n);r=read(name);K=-1000*r['patches']['front_seat']['mean_displacement_mm_at_E1000'][1];Kr=-1000*r['patches']['rear_seat']['mean_displacement_mm_at_E1000'][1];E=m['young_modulus_XY_MPa'];delta=K/E
  row={'material':label,'walls':n,'source_mesh':name,'reference_E_MPa':E,'front_K_MPa_mm':K,'rear_K_MPa_mm':Kr,'initial_front_mm':delta,'one_roll_initial_mm_upper_simple_case':delta*1.25/12,'minimum_creep_modulus_MPa_for_5mm_bracket_only':K/5,'compliance_multiplier_limit_bracket_only':5/delta,'source_url':m['source_url']}
  summary['cases'].append(row);rows.append(f'| {label} | {n} | {E:.0f} | {delta:.2f} | {delta*1.25/12:.3f} | {K/5:.0f} | {5/delta:.2f}× |')
 for n in [8,10]:
  coarse=f'print-material-{n}w-h3';fine=f'print-material-{n}w-h2'
  if (D/f'{fine}-results.json').exists():
   a=read(coarse);b=read(fine);da=-a['patches']['front_seat']['mean_displacement_mm_at_E1000'][1];db=-b['patches']['front_seat']['mean_displacement_mm_at_E1000'][1]
   summary['mesh_checks'].append({'rear_seat_p99_coarse_MPa':a['regions']['rear_seat']['vm_p99_MPa'],'rear_seat_p99_fine_MPa':b['regions']['rear_seat']['vm_p99_MPa'],'walls':n,'coarse_tets':a['tetrahedra'],'fine_tets':b['tetrahedra'],'front_displacement_change_percent':100*(db/da-1),'coarse_VM_p99_MPa':a['vm_volume_p99_MPa'],'fine_VM_p99_MPa':b['vm_volume_p99_MPa'],'coarse_VM_max_MPa':a['vm_max_MPa_not_allowable'],'fine_VM_max_MPa':b['vm_max_MPa_not_allowable']})
 # Figure 26 visually transcribed spectrum, seconds; normalized example only.
 tau=np.array([1,10,100,1000,10000,100000.]);A=np.array([.005,.010,.015,.010,.020,.080])
 def G(t):return 1+np.sum(A*(1-np.exp(-np.asarray(t)[...,None]/tau)),axis=-1)
 summary['published_PETG_example']={'source':'https://doi.org/10.3390/polym17152075','tau_seconds':tau.tolist(),'A_dimensionless':A.tolist(),'transcription':'Figure 26 bar heights; approximate graphical values','G_5h':float(G(5*3600)),'G_20h':float(G(20*3600)),'formal_plateau':float(1+A.sum()),'scope':'Devil Design, unidirectional 100% specimens, 21.3 C; tested to 20 h. Formal plateau is not established multi-year behavior.'}
 summary['thermal_shift_scenarios']=[]
 R=8.314462618;Tref=273.15+(85-32)*5/9;Thot=273.15+(100-32)*5/9
 for Q in [50,100,200]:
  rate=np.exp(Q*1000/R*(1/Tref-1/Thot));summary['thermal_shift_scenarios'].append({'assumed_activation_kJ_mol':Q,'hot_rate_factor':rate,'equivalent_hours_per_year':8754+6*rate,'extra_time_percent':100*6*(rate-1)/8760})
 summary['planning_scenarios']=[]
 for year in [1,5,10]:
  for tail in [0,.02,.10]:
   row={'years':year,'assumed_unmeasured_linear_compliance_tail_per_year':tail,'G':float(G(year*365*86400)+tail*year)}
   for c in summary['cases'][:2]:row[c['material']+'_front_mm']=row['G']*c['initial_front_mm']
   summary['planning_scenarios'].append(row)
 summary['raised_front_statics']=raised_front()
 # Creep graph distinguishes observed range from unmeasured continuation.
 fig,ax=plt.subplots(1,2,figsize=(12,5),layout='constrained');hours=np.geomspace(.001,20,240);ax[0].semilogx(hours,G(hours*3600),color='#187d83',lw=2);ax[0].set(xlabel='Hours',ylabel='Normalized compliance J / J0',title='Published PETG spectrum • tested time range')
 years=np.linspace(0,10,300)
 for tail in [0,.02,.1]:ax[1].plot(years,G(years*365*86400)+tail*years,label=f'Unmeasured tail: {tail:.2f} / year')
 ax[1].set(xlabel='Years',ylabel='Normalized compliance J / J0',title='Sensitivity only • not service-life predictions');ax[1].legend()
 for a in ax:a.grid(alpha=.2)
 fig.supxlabel('Short-time spectrum: Stankevics et al. (2025), Fig. 26. Temperature shifts and long-time tails are uncalibrated.\nA fitted finite Prony series plateaus by construction; this does not prove the printed bracket stops creeping.',fontsize=9)
 fig.savefig(D/'creep-sensitivity.png',dpi=160);plt.close(fig)
 land='landing-8w-h0.65' if (D/'landing-8w-h0.65-results.json').exists() else 'landing-8w-h1'
 render2('plane-8w-h1');render3(best(8),'fem-3d.png');render3(land,'fem-landing.png',True)
 (D/'engineering-summary.json').write_text(json.dumps(summary,indent=2))
 text='# Solved E9 engineering results\n\nThese results apply to the raised-front E9 prototype, including its reshaped back arm and 2 mm broad-face chamfers. The rail-statics comparison isolates the effect of the 12 mm height change.\n\n'
 text+='| Material | Walls | Reference E (MPa) | Initial front movement (mm) | One 1.25 kg roll (mm) | Creep modulus needed for 5 mm (MPa) | Compliance limit |\n|---|---:|---:|---:|---:|---:|---:|\n'+'\n'.join(rows)
 text+='\n\nModuli are room-temperature reference values. The creep-modulus limits apply to bracket movement alone; subtract dowel and wall movement from the 5 mm system allowance. The one-roll column assigns the entire roll reaction to one bracket, for the stated simple/two-equal-span arrangement, and uses the reference instantaneous modulus. It is not a measured aged unloading modulus.\n\n'
 text+='## Numerical checks\n\n'
 for c in summary['mesh_checks']:text+=f'- {c["walls"]} walls: {c["coarse_tets"]:,} → {c["fine_tets"]:,} tetrahedra; front movement changes {c["front_displacement_change_percent"]:.2f}%. Volume p99 stress: {c["coarse_VM_p99_MPa"]:.2f} → {c["fine_VM_p99_MPa"]:.2f} MPa. Raw peak: {c["coarse_VM_max_MPa"]:.2f} → {c["fine_VM_max_MPa"]:.2f} MPa.\n'
 if not summary['mesh_checks']:text+='Whole-bracket refinement is pending.\n'
 text+='\nA percentile is a field summary, not a stress allowable. The refinement changes listed above do not establish asymptotic convergence. Regional stress changes must also be considered; global percentiles can hide local changes. Tiny cells at tunnel/chamfer intersections, sharp analysis-core transitions and restraint edges affect peaks; actual sliced radii and FFF anisotropy require separate interpretation. See individual result JSON files for force/moment balance, residuals, patch movements and regional stresses.\n\n![2D FEM](fem-2d.png)\n\n![3D FEM](fem-3d.png)\n\n![Landing FEM](fem-landing.png)\n\n![Creep sensitivity](creep-sensitivity.png)\n\n![Raised-front study](raised-front-statics.png)\n\n'
 text+='## Conditional one-, five- and ten-year calculation\n\n| Years | Assumed extra compliance / year | Total compliance multiplier | PLA movement (mm) | PETG movement (mm) |\n|---:|---:|---:|---:|---:|\n'
 for c in summary['planning_scenarios']:text+=f'| {c["years"]} | {c["assumed_unmeasured_linear_compliance_tail_per_year"]:.2f} | {c["G"]:.2f} | {c["PLA_front_mm"]:.2f} | {c["PETG_front_mm"]:.2f} |\n'
 text+='\nThese curves intentionally demonstrate different long-term continuations that a short test cannot distinguish. They are neither PLA nor PETG life predictions at 85°F. No creep-rupture allowable is inferred.\n'
 (D/'RESULTS.md').write_text(text)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
