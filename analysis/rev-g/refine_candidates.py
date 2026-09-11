"""Refine a diverse low-mass shortlist from completed genetic runs."""
import argparse
import json
from pathlib import Path
from fast_screen import Screen, D, ROOT, source_hash


def main(run_names, count):
    records = {}
    for name in run_names:
        run = json.loads((D/'runs'/name/'summary.json').read_text())
        folder = D/'search-evidence'/run['search_signature'][:16]
        for ident in run['evaluated_candidate_ids']:
            row = json.loads((folder/f'candidate-{ident}.json').read_text())
            if row['status'] == 'SCREEN_FEASIBLE':
                records[ident] = row
    ordered = sorted(records.values(), key=lambda r: (r['score'], r['id']))
    selected = []
    groups = {}
    for row in ordered:
        p = row['parameters']
        key = tuple(p[k] for k in ['walls', 'skin_mm', 'plane_mm', 'planes', 'window_scale'])
        if groups.get(key, 0) >= 2:
            continue
        selected.append(row)
        groups[key] = groups.get(key, 0)+1
        if len(selected) >= count:
            break
    # Include designs with more movement/strength reserve, even if a mass-only
    # coarse shortlist would omit them. Final acceptance is still in 3D.
    extra = [r for r in ordered if r['result']['front_movement_mm_at_E1000'] <= 3.6
             and r['result']['conservative_40p5MPa_strength_ratio'] >= 4.8]
    for row in extra[:3]:
        if row not in selected:
            selected.append(row)
    models = {}
    out = D/'refinements'
    out.mkdir(exist_ok=True)
    rows = []
    for candidate in selected:
        ident, p = candidate['id'], candidate['parameters']
        saved = out/f'{ident}-h1-full.json'
        if saved.exists():
            result = json.loads(saved.read_text())
            assert result['evaluator_source_hash'] == source_hash()
        else:
            scale = p['window_scale']
            if scale not in models:
                models[scale] = Screen(h=1, window_scale=scale)
            result = models[scale].solve(p, field_path=out/f'{ident}-h1-full-solution.npz')
            result.pop('elapsed_seconds', None)
            result['candidate_id'] = ident
            result['evaluator_source_hash'] = source_hash()
            result['coarse_front_movement_mm_at_E1000'] = candidate['result']['front_movement_mm_at_E1000']
            result['coarse_mass_proxy_g_at_1p24'] = candidate['result']['nominal_mass_proxy_g_at_1p24']
            result['passes_refined_screen'] = result['front_movement_mm_at_E1000'] <= 4 and result['raw_peak_tensile_MPa'] <= 10.125
            saved.write_text(json.dumps(result, indent=2)+'\n')
        rows.append(result)
        (D/'refined-shortlist.json').write_text(json.dumps(rows, indent=2)+'\n')
        print('REFINED', ident, 'mass proxy', result['nominal_mass_proxy_g_at_1p24'],
              'front', result['front_movement_mm_at_E1000'], 'tensile', result['raw_peak_tensile_MPa'],
              'pass', result['passes_refined_screen'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args()
    main(args.runs, args.count)
