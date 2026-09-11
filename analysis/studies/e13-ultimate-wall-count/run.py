"""Reproduce the archived E13 reduced wall-count screen."""
from pathlib import Path
import sys,json
import numpy as np
D=Path(__file__).resolve().parent
base=D.parents[1]/'e13'
sys.path.insert(0,str(base))
import solve_comparison as solver
solver.D=D
rows=[]
for n in [2,3,4,6,8,10]:
    name=f'e13-{n}w-h1-full'
    if n in [8,10]:
        result=json.loads((base/f'{name}-results.json').read_text())
        field=np.load(base/f'{name}-solution.npz')
    else:
        result=solver.solve('e13',n,1,'full')
        field=np.load(D/f'{name}-solution.npz')
    vm=field['vm'];principal=field['principal'];volume=field['volume'];c=field['p'][field['t']].mean(1)
    i=int(principal.argmax());j=int(vm.argmax())
    row={'walls':n,'model':'layer-integrated plane stress; does not resolve 3D hot spots',
         'raw_peak_tensile_principal_MPa':float(principal[i]),'tensile_peak_xy':c[i].tolist(),
         'raw_peak_VM_MPa':float(vm[j]),'VM_peak_xy':c[j].tolist(),
         'whole_body_VM_p99_MPa':solver.quantile(vm,volume,.99),
         'whole_body_tensile_p99_MPa':solver.quantile(principal,volume,.99),
         'seat_VM_p99_MPa':result['regions']['near_rear_seat_fixed_window']['vm_volume_p99_MPa'],
         'reference_XY_PLA_UTS_over_tensile_peak':52.3/float(principal[i]),
         'reference_XY_PETG_UTS_over_tensile_peak':47.96/float(principal[i]),
         'relative_free_residual':result['relative_free_residual']}
    rows.append(row);print(json.dumps(row),flush=True)
(D/'screen.json').write_text(json.dumps({'load_kg_per_bracket':12,'four_1p2mm_plates_preserved':True,'zero_sparse_infill_credit':True,'cases':rows},indent=2)+'\n')
