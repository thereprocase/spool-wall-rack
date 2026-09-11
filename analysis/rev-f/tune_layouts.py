"""Tune shell count around the dense load paths, retaining the shaped planes."""
import json
from screen_layouts import screen,D
common={'window_scale':1.,'bottom_band':5.,'diagonal_band':5.,'seat_band':12.,
        'front_seat_band':3.,'planes':'shaped','rib_frame':6.,'seat_webs':True,'infill_percent':8}
rows=[]
for walls in [2,3,4]:
    for band in [5.,6.]:
        params={**common,'name':f'f-tuned-{walls}w-{band:g}','walls':walls,'bottom_band':band,'diagonal_band':band}
        try:
            row=screen(params);rows.append(row);print('SCREEN',json.dumps(row),flush=True)
        except RuntimeError as error:
            rows.append({'name':params['name'],'parameters':params,'status':'REJECTED','reason':str(error)})
        (D/'screening-tuned.json').write_text(json.dumps(rows,indent=2)+'\n')
