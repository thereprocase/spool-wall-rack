"""Minimize nominal printed mass inside service/strength screens; baseline is a reference."""
import json
from screen_layouts import screen,D

base={'window_scale':1.,'walls':2,'skin_mm':.8,'plane_mm':.8,'bottom_band':1.8,'diagonal_band':1.8,
      'seat_band':4.,'front_seat_band':2.,'planes':'full','rib_frame':4.,'seat_webs':True,
      'infill_percent':5,'lower_tunnel_collar_mm':3.5,'upper_tunnel_collar_mm':2.}
variants=[('light-full',{}),('light-shaped',{'planes':'shaped'}),
          ('thin-full',{'skin_mm':.6,'plane_mm':.6}),('thin-shaped',{'skin_mm':.6,'plane_mm':.6,'planes':'shaped'}),
          ('skin-06',{'skin_mm':.6}),('planes-06',{'plane_mm':.6}),
          ('1w-full',{'walls':1}),('1w-thin',{'walls':1,'skin_mm':.6,'plane_mm':.6}),
          ('1w-shaped',{'walls':1,'planes':'shaped'}),
          ('3w-thin',{'walls':3,'skin_mm':.6,'plane_mm':.6,'bottom_band':1.2,'diagonal_band':1.2}),
          ('lean-chords',{'bottom_band':1.2,'diagonal_band':1.2}),
          ('lean-seat',{'seat_band':2.5}),
          ('lean-all',{'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5,'front_seat_band':1.5}),
          ('thin-lean',{'skin_mm':.6,'plane_mm':.6,'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5}),
          ('1w-lean',{'walls':1,'skin_mm':.6,'plane_mm':.6,'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5}),
          ('1w-rib',{'walls':1,'skin_mm':.6,'plane_mm':.6,'planes':'shaped','rib_frame':3.,'bottom_band':2.2,'diagonal_band':2.2})]
rows=[]
for label,change in variants:
    params={**base,**change,'name':'f-limit-'+label}
    try:
        result=screen(params,h=2)
        case=result['load_cases']['full'];mass=result['nominal_print_volume_mm3']/1000*1.24
        case['conservative_40p5MPa_strength_ratio']=40.5/case['raw_peak_tensile_MPa']
        case['remaining_5mm_budget_at_Ec1000_mm']=5-case['front_movement_mm_at_E1000']
        case['one_spool_movement_at_E1000_mm']=case['front_movement_mm_at_E1000']*1.25/12
        result['nominal_mass_g_at_1p24']=mass
        result['relative_stiffness_per_gram_to_E13_8w']=2.05435075436763*167.11/(case['front_movement_mm_at_E1000']*mass)
        result['screen_feasible']=case['conservative_40p5MPa_strength_ratio']>=4 and case['front_movement_mm_at_E1000']<5 and case['one_spool_movement_at_E1000_mm']<1
        rows.append(result)
        print('LIMIT',json.dumps(result),flush=True)
    except (AssertionError,RuntimeError) as error:
        rows.append({'name':params['name'],'parameters':params,'screen_feasible':False,'rejection':str(error)})
        print('REJECTED',params['name'],str(error),flush=True)
    (D/'constrained-screening.json').write_text(json.dumps(rows,indent=2)+'\n')
