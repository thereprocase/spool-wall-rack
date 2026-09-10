"""Wall-count mapping and ideal straight-forearm stiffness; not a capacity check."""
from pathlib import Path
import json,math
D=Path(__file__).resolve().parent
refs=json.loads((D.parent/'closed-wall-e6/material-reference-data.json').read_text())['cases']
E={r['case']:r['flexural_modulus_XY_MPa'] for r in refs}
layer=.2;outer_width=.42;inner_width=.45
b=24;h=28;plate_total=4*1.2;V=12*9.81/2;L=100
rows=[]
for n in [3,4,6,8,9,10,12]:
 t=outer_width+(n-1)*(inner_width-layer*(1-math.pi/4))
 A=b*h-(b-plate_total)*(h-2*t)
 I=(b*h**3-(b-plate_total)*(h-2*t)**3)/12
 rows.append({'wall_count':n,'estimated_perimeter_thickness_mm':t,'area_mm2':A,'I_mm4':I,
  'reference_vertical_forearm_deflection_mm':{m:V*L**3/(3*E[m]*I) for m in ['PLA','PETG']}})
report={'status':'Prototype settings and ideal local stiffness screen; no verified adequate load or creep life.',
 'starting_wall_counts':{'PLA':8,'PETG':10},'layer_height_mm':layer,
 'assumed_outer_line_width_mm':outer_width,'assumed_inner_line_width_mm':inner_width,
 'line_widths_are_assumptions_not_asserted_printer_defaults':True,
 'section_width_mm':b,'section_depth_mm':h,'solid_plate_total_mm':plate_total,
 'bracket_load_target_kg_equivalent':12,'front_seat_vertical_N':V,
 'forearm_span_mm':L,'rows':rows,
 'sources':['https://manual.slic3r.org/advanced/flow-math','../closed-wall-e6/material-reference-data.json'],
 'limitations':['Approximate fixed-width extrusion-spacing model; actual slicer wall paths govern.',
 'Uniform rectangular forearm with fixed rear seat; ignores outward thrust, wall joint, knee, bevels, shear and variable geometry.',
 'Reference material moduli are typical specimen values, not 85 F long-term creep moduli.',
 '8 PLA and 10 PETG are engineering prototype selections, not calculated minimum wall counts or equal-stiffness solutions.',
 'Do not turn this local deflection screen into a whole-bracket strength or spool rating.']}
(D/'wall-count-screen.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:print(r['wall_count'],round(r['estimated_perimeter_thickness_mm'],2),{k:round(v,3)for k,v in r['reference_vertical_forearm_deflection_mm'].items()})
