"""Second bounded sweep: retain the best stiffness/weight tradeoffs."""
from pathlib import Path
import json
from screen_layouts import screen,WORK,D,material_layers

common={'walls':4,'window_scale':1.,'bottom_band':4.3,'diagonal_band':4.3,
        'seat_band':7.,'front_seat_band':3.,'planes':'full','infill_percent':8}
candidates=[{**common,'name':'f-balanced'},
 {**common,'name':'f-wide-window','window_scale':1.12,'bottom_band':5.4,'diagonal_band':5.4},
 {**common,'name':'f-shaped-webs','planes':'shaped','rib_frame':6.,'seat_webs':True,'bottom_band':5.,'diagonal_band':5.},
 {**common,'name':'f-shaped-seat9','planes':'shaped','rib_frame':6.,'seat_webs':True,'seat_band':9.,'bottom_band':5.,'diagonal_band':5.},
 {**common,'name':'f-shaped-seat11','planes':'shaped','rib_frame':6.,'seat_webs':True,'seat_band':11.,'bottom_band':5.,'diagonal_band':5.},
 {**common,'name':'f-shaped-chords6','planes':'shaped','rib_frame':6.,'seat_webs':True,'bottom_band':6.,'diagonal_band':6.}]
rows=[]
for params in candidates:
    try:
        row=screen(params);print('SCREEN',json.dumps(row),flush=True);rows.append(row)
    except RuntimeError as error:
        row={'name':params['name'],'parameters':params,'status':'REJECTED','reason':str(error)}
        rows.append(row);print('REJECTED',json.dumps(row),flush=True)
    (D/'screening-refinement.json').write_text(json.dumps(rows,indent=2)+'\n')
upper={**common,'name':'f-upper-window-proxy','upper_window':True,'bottom_band':5.,'diagonal_band':5.}
_,proxy=material_layers(upper)
(D/'upper-window-volume-proxy.json').write_text(json.dumps({'parameters':upper,**proxy,'note':'Initial h2 solve failed contact convergence; no structural result accepted.'},indent=2)+'\n')
