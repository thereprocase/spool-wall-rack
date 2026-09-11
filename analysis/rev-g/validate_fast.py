"""Compare the accelerated solver with four preserved canonical solved fields."""
from pathlib import Path
import json
import time
import numpy as np
from fast_screen import Screen, D, ROOT, source_hash


def main():
    cases = [
        ('E13-eight-wall',
         {'walls': 8, 'window_scale': 0., 'skin_mm': 1.2, 'plane_mm': 1.2,
          'planes': 'full', 'baseline': True, 'infill_percent': 15},
         ROOT/'analysis/e13/e13-8w-h1-full-solution.npz', 1),
        ('F-three-wall-shaped',
         json.loads((ROOT/'designs/rev-f/selected-layout.json').read_text()),
         ROOT/'analysis/rev-f/studies/reduced-fields/f-final-3w/f-final-3w-3w-h1-full-solution.npz', 1),
        ('F-four-wall-full',
         json.loads((ROOT/'analysis/rev-f/full-plane-layout.json').read_text()),
         ROOT/'analysis/rev-f/studies/reduced-fields/f-final-full-planes/f-final-full-planes-4w-h1-full-solution.npz', 1),
        ('F-light-one-wall',
         json.loads((ROOT/'analysis/rev-f/light-full-layout.json').read_text()),
         ROOT/'analysis/rev-f/studies/reduced-fields/f-limit-1w-full/f-limit-1w-full-1w-h2-full-solution.npz', 2),
    ]
    rows = []
    for label, params, path, h in cases:
        started = time.perf_counter()
        model = Screen(h=h, window_scale=params['window_scale'], mesh_path=path)
        output = D/'.work'/f'validation-{label}.npz'
        result = model.solve(params, field_path=output)
        repeat = model.solve(params)
        with np.load(path) as expected, np.load(output) as actual:
            max_u_error = float(abs(actual['u']-expected['u']).max())
            max_stress_error = float(abs(actual['stress']-expected['stress']).max())
            max_thickness_error = float(abs(actual['thickness']-expected['thickness']).max())
        assert max_thickness_error < 1e-10, (label, max_thickness_error)
        assert max_u_error < 1e-6 and max_stress_error < 1e-5, (label, max_u_error, max_stress_error)
        numerical_keys = ['front_movement_mm_at_E1000', 'rear_movement_mm_at_E1000',
                          'raw_peak_tensile_MPa', 'load_compliance_Nmm_at_E1000',
                          'nominal_mass_proxy_g_at_1p24']
        assert all(abs(result[k]-repeat[k]) < 1e-10 for k in numerical_keys)
        row = {'case': label, 'canonical_field': path.relative_to(ROOT).as_posix(),
               'maximum_displacement_error_mm': max_u_error,
               'maximum_stress_component_error_MPa': max_stress_error,
               'maximum_integrated_thickness_error_mm': max_thickness_error,
               'uncached_repeat_matches': True, 'result': result,
               'including_preparation_seconds': time.perf_counter()-started}
        rows.append(row)
        print(label, json.dumps({k: v for k, v in row.items() if k != 'result'}), flush=True)
        (D/'fast-screen-validation.json').write_text(json.dumps({'source_hash': source_hash(),
            'status': 'PASS' if len(rows) == len(cases) else 'IN_PROGRESS', 'cases': rows}, indent=2)+'\n')


if __name__ == '__main__':
    main()
