"""Ideal multi-cell rectangular section sensitivity, not revised CAD or load rating."""
import json
from pathlib import Path
D=Path(__file__).resolve().parent

def section(width,depth,perimeter,plate_count=4,plate_thickness=1.2):
    # Sum cavity widths; interior voids all have the same clear vertical depth.
    void_width=width-plate_count*plate_thickness
    void_depth=depth-2*perimeter
    area=width*depth-void_width*void_depth
    inertia=(width*depth**3-void_width*void_depth**3)/12
    return {'width_mm':width,'depth_mm':depth,'perimeter_mm':perimeter,
            'continuous_plates':plate_count,'plate_thickness_mm':plate_thickness,
            'area_mm2':area,'I_mm4':inertia,'S_mm3':2*inertia/depth}

base=section(24,28,2.4)
rows=[]
for name,args in [('E6 idealized baseline',(24,28,2.4)),
                  ('Thicker perimeter only',(24,28,3.6)),
                  ('One additional plate only',(24.4,28,2.4,5)),
                  ('Moderate depth',(24,32,3.6)),
                  ('Shared PLA PETG study candidate',(24,34,3.6)),
                  ('Deeper sensitivity',(24,36,3.6))]:
    q=section(*args)
    q['name']=name
    for prop in ['area_mm2','I_mm4','S_mm3']:
        q[prop+'_ratio_to_baseline']=q[prop]/base[prop]
    q['pure_bending_stress_ratio']=base['S_mm3']/q['S_mm3']
    rows.append(q)
refs=json.loads((D/'material-reference-data.json').read_text())['cases']
modulus={r['case']:r['flexural_modulus_XY_MPa'] for r in refs}
candidate=rows[4]
result={'status':'Sizing study only; E6 CAD unchanged and no load rating assigned.',
        'sections':rows,
        'candidate_initial_EI_relative_to_ASA_baseline':{
            m:candidate['I_mm4_ratio_to_baseline']*modulus[m]/modulus['ASA']
            for m in ['PLA','PETG','PETG legacy sensitivity']},
        'limitations':[
            'Rectangular straight-arm approximation omits chamfers, cavity-rim reinforcement, local geometry and screw sleeves.',
            'Ratios describe pure bending and local straight-arm material, not whole-bracket stiffness, combined peak stress or total print mass.',
            'Section increase must continue through the demanding knee; it is not a retrofit confined to midspan.',
            'Keep spool track and snap geometry fixed; add depth below the arm and blend the transition.',
            'No grade-specific creep modulus at the stated temperature and service life is available; these dimensions cannot guarantee creep life.',
            'More plates alone do not resolve unsupported cavity roofs.',
        ]}
(D/'material-sizing.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['candidate_initial_EI_relative_to_ASA_baseline'],indent=2))
