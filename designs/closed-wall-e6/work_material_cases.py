"""Reproducible load cases, not capacities or predictions of creep life.

Run check_material_sections.py first if the final CAD changes.
Reference deflection is a vertical-load-only prismatic forearm comparison.
"""
from pathlib import Path
import json
import math

D = Path(__file__).resolve().parent
sections = json.loads((D / 'section-load-screen.json').read_text())['sections']
references = json.loads((D / 'material-reference-data.json').read_text())
mass = 12.0
weight = mass * 9.81
vertical = weight / 2
diameter_cases = []
for diameter in (180, 200, 220):
    # Seated rod moves 0.3 mm from seat center, away from spool.
    center_distance = diameter / 2 + 12.7 - 0.3
    outward = vertical * 50 / math.sqrt(center_distance**2 - 50**2)
    rows = []
    for s in sections:
        x = s['x_from_wall_mm']
        moment = (weight * (140 - x) if x < 90 else
                  vertical * (190 - x) + outward * abs(s['centroid_y_mm']))
        axial = 0 if x < 90 else outward
        stress = moment / s['minimum_elastic_section_modulus_mm3'] + axial / s['area_mm2']
        rows.append({'x_mm': x, 'nominal_stress_MPa': stress})
    diameter_cases.append({'spool_diameter_mm': diameter,
                           'each_seat_vertical_N': vertical,
                           'each_seat_outward_N': outward,
                           'sampled_sections': rows,
                           'maximum_sampled_nominal_stress_MPa': max(r['nominal_stress_MPa'] for r in rows)})

inertia = next(s['I_about_width_axis_mm4'] for s in sections if s['x_from_wall_mm'] == 140)
materials = []
for reference in references['cases']:
    materials.append({
        'case': reference['case'],
        'reference_grade': reference['reference_grade'],
        'reference_only_vertical_forearm_deflection_mm': vertical * 100**3 / (3 * reference['flexural_modulus_XY_MPa'] * inertia),
        'qualified_sustained_capacity_kg': None,
        'qualified_spools_per_bay': None,
        'creep_life_hours': None,
    })
peak = max(c['maximum_sampled_nominal_stress_MPa'] for c in diameter_cases)
report = {
    'status': 'Design and proposed qualification cases only; no material has a released load rating.',
    'service_temperature_F': 85,
    'service_temperature_C': (85 - 32) * 5 / 9,
    'hot_temperature_F': 100,
    'hot_temperature_C': (100 - 32) * 5 / 9,
    'hot_hours_per_year': 6,
    'sustained_and_hot_bracket_load_target_kg_equivalent': mass,
    'chosen_short_proof_load_target_kg_equivalent': mass * 2,
    'wall_moment_Nm': weight * .14,
    'ideal_upper_screw_tension_N': weight * .14 / .196,
    'diameter_cases': diameter_cases,
    'highest_sampled_service_nominal_stress_MPa': peak,
    'linear_screen_at_chosen_proof_load_MPa': peak * 2,
    'material_cases': materials,
    'limitations': [
        '12 kg is a rounded design target, not an allowable load or universal reaction bound.',
        'Both service and hot cases carry the full load. Six hot hours are not averaged away.',
        'All modeled solid assumed fully printed; no infill or empty-cavity strength credit.',
        'Nominal sections omit local stress concentrations, wall connection, snap-root strain, shear and plate buckling.',
        'Reference deflection uses published typical flexural modulus, a fixed rear seat and a uniform 100 mm forearm with midpoint inertia. It omits outward load, other bracket compliance, service temperature and creep.',
        'HDT, Tg, tensile strength and elongation at break do not define long-term allowable loads or snap strain.',
        'A short proof test and 1000-hour trial do not establish a multi-year creep life.',
    ],
}
(D / 'material-work-cases.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('diameter_cases', 'limitations')}, indent=2))
