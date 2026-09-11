"""Check finalist layouts at 1 mm under combined and outer-seat-only loads."""
import json
from screen_layouts import screen,D
common={'window_scale':1.,'bottom_band':5.,'diagonal_band':5.,'seat_band':12.,
        'front_seat_band':3.,'planes':'shaped','rib_frame':6.,'seat_webs':True,'infill_percent':8}
candidates=[
 {**common,'name':'f-final-2w','walls':2,'bottom_band':6.4,'diagonal_band':6.4,'seat_band':13.},
 {**common,'name':'f-final-3w','walls':3,'bottom_band':6.,'diagonal_band':6.},
 {**common,'name':'f-final-4w','walls':4},
 {**common,'name':'f-final-full-planes','walls':4,'planes':'full','seat_band':7.,'bottom_band':4.3,'diagonal_band':4.3}]
rows=[]
for params in candidates:
    try:
        row=screen(params,h=1,load_cases=('full','outer_only'));rows.append(row)
        print('FINALIST',json.dumps(row),flush=True)
    except RuntimeError as error:
        rows.append({'name':params['name'],'parameters':params,'status':'REJECTED','reason':str(error)})
        print('REJECTED',params['name'],str(error),flush=True)
    (D/'finalist-screening.json').write_text(json.dumps(rows,indent=2)+'\n')
