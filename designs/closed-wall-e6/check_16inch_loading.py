"""Service demand screen, not an allowable load or installation approval."""
from pathlib import Path
import math,json
D=Path(__file__).resolve().parent
L=406.4; count=6; gross_mass=1.25; g=9.81
bay_mass=count*gross_mass; bay_weight=bay_mass*g
section=json.loads((D/'vertical-verification.json').read_text())['revisions']['E6']['sections'][0]
h=math.sqrt(112.4**2-50**2);H_over_V=50/h
middle_mass=1.25*bay_mass;middle_weight=middle_mass*g
V=middle_weight/2;H=V*H_over_V
M=V*50+H*abs(section['centroid_y_mm'])
stress=M/section['minimum_elastic_section_modulus_mm3']+H/section['area_mm2']
d=25.4;I=math.pi*d**4/64;Z=math.pi*d**3/32;E_assumed=8000
rod_resultant=(bay_weight/2)*math.sqrt(1+H_over_V**2)
report={
 'status':'SERVICE DEMAND ONLY — no safe spool count or creep rating',
 'bracket_spacing_mm':L,'spools_per_bay_assumed':count,'gross_mass_per_spool_kg_assumed':gross_mass,
 'maximum_spool_pitch_for_six_per_bay_mm':L/count,
 'bay_spool_mass_kg':bay_mass,
 'isolated_single_bay_end_support_mass_equivalent_kg':bay_mass/2,
 'interior_support_adjacent_simple_spans_mass_equivalent_kg':bay_mass,
 'two_equal_continuous_spans_middle_support_mass_equivalent_kg':middle_mass,
 'two_span_middle_wall_moment_Nm':middle_weight*.14,
 'two_span_middle_idealized_upper_screw_tension_N':middle_weight*.14/.196,
 'two_span_middle_each_seat_vertical_N':V,
 'two_span_middle_each_seat_outward_N':H,
 'two_span_middle_midpoint_nominal_extreme_stress_screen_MPa':stress,
 'wood_rod_simple_span_screen':{'elastic_modulus_assumed_MPa':E_assumed,'combined_bending_stress_MPa':rod_resultant*L/8/Z,'instantaneous_resultant_deflection_mm':5*rod_resultant*L**3/(384*E_assumed*I)},
 'dense_row_mass_sensitivity':[{'spool_pitch_mm':pitch,'gross_mass_kg_per_spool':gross_mass,'tributary_mass_kg':L/pitch*gross_mass,'two_span_middle_mass_equivalent_kg':1.25*L/pitch*gross_mass} for pitch in [60,65,70]],
 'assumptions':['Uniformly distributed spool weight and equal vertical load sharing between two rods. Six discrete spools and clustered loading will differ.','The 1.25 factor is the elastic reaction for two equal continuous beam spans under equal uniform loads. It is not a universal reaction bound or safety factor.','No rail overhangs, support settlement, dowel self-weight, accidental loads or dynamic amplification included.','The printed bracket midpoint stress includes bending from vertical/outward front-seat forces and axial stress, using final CAD section properties. It excludes stress concentrations, snap roots, the knee, shear, buckling and time-dependent behavior.','Wood modulus is an explicit 8 GPa calculation assumption, not a measured property or a grade/species assignment for the purchased dowels.','The screw-force estimate assumes one upper tension screw and a compression point at the bottom of the wall face. It is a demand estimate, not a fastener capacity check.'],
 'release_gates':['Identify bracket filament, temperature, duration and required spool loading.','Resolve the unsupported internal roofs and inspect actual sliced solid paths.','Analyze critical bracket sections and mounting fasteners; verify creep behavior and handling with representative prints.']}
(D/'loading-16inch.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
