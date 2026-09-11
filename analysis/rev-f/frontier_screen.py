"""Refine the light feasible frontier without restoring baseline stiffness."""
import json
from screen_layouts import screen,D
rows=json.loads((D/'constrained-screening.json').read_text())
base=next(r['parameters'] for r in rows if r['name']=='f-limit-1w-full')
variants=[('1w-lean-full',{'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5}),
          ('1w-lean-skin06',{'skin_mm':.6,'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5}),
          ('1w-lean-plane06',{'plane_mm':.6,'bottom_band':1.2,'diagonal_band':1.2,'seat_band':2.5}),
          ('1w-thin-seat3',{'skin_mm':.6,'plane_mm':.6,'bottom_band':1.2,'diagonal_band':1.2,'seat_band':3.}),
          ('1w-thin-chord15',{'skin_mm':.6,'plane_mm':.6,'bottom_band':1.5,'diagonal_band':1.5,'seat_band':2.5})]
out=[]
for label,change in variants:
    params={**base,**change,'name':'f-frontier-'+label}
    try:out.append(screen(params,h=1,load_cases=('full','outer_only')))
    except (AssertionError,RuntimeError) as error:out.append({'name':params['name'],'parameters':params,'rejection':str(error)})
    (D/'frontier-screening.json').write_text(json.dumps(out,indent=2)+'\n')
    print('FRONTIER',json.dumps(out[-1]),flush=True)
