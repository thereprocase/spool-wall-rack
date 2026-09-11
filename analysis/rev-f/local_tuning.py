"""Bounded local reinforcements after the full 3D stiffness comparison."""
import json
from screen_layouts import screen,D
base=json.loads((D/'full-plane-layout.json').read_text())
variants=[('front-collar',{'front_seat_band':4.}),('lower-chord',{'bottom_band':4.8}),
          ('diagonal',{'diagonal_band':4.8}),('inner-collar',{'seat_band':8.})]
rows=[]
for label,changes in variants:
    params={**base,**changes,'name':'f-local-'+label}
    result=screen(params,h=2);rows.append(result)
    print('LOCAL',json.dumps(result),flush=True)
    (D/'local-tuning.json').write_text(json.dumps(rows,indent=2)+'\n')
