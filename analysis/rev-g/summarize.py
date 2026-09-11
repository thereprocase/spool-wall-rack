"""Summarize saved Rev G search and raw fields; never replace failed gates."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CAD = ROOT/'designs/rev-g'
RUNS = ['seed-20260910-h2', 'seed-20260911-h2',
        '3d-feedback-seed-20260912-h2']


def write(name, value):
    (D/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def search_summary():
    rows, union = [], {}
    for name in RUNS:
        run = json.loads((D/'runs'/name/'summary.json').read_text())
        folder = D/'search-evidence'/run['search_signature'][:16]
        records = [json.loads((folder/f'candidate-{i}.json').read_text())
                   for i in run['evaluated_candidate_ids']]
        for r in records:
            union[r['id']] = r
        best = run['best_candidate']
        rows.append({'run': name, 'seed': run['seed'],
                     'population_size': run['population_size'],
                     'generations': run['generations'],
                     'search_signature': run['search_signature'],
                     'unique_evaluated_in_run': len(records),
                     'candidate_status_counts': dict(Counter(r['status'] for r in records)),
                     'best_candidate_id': best['id'],
                     'best_parameters': best['parameters'],
                     'best_mass_proxy_g': best['result']['nominal_mass_proxy_g_at_1p24'],
                     'best_screen_front_mm': best['result']['front_movement_mm_at_E1000'],
                     'best_screen_raw_tensile_MPa': best['result']['raw_peak_tensile_MPa'],
                     'generation_ledger_sha256': run['generation_ledger_sha256']})
    value = {'unique_parameter_sets_all_runs': len(union), 'runs': rows,
             'scope': 'Coarse plane-stress screening only; mass is a quadrature proxy, and SCREEN_FEASIBLE is not a 3D or printing qualification.',
             'global_optimum_proven': False}
    write('search-summary.json', value)
    return value


def field_metrics(folder, name, cad_folder):
    report_path = folder/(name+'-results.json')
    raw_path = folder/(name+'-solution.npz')
    report = json.loads(report_path.read_text())
    with np.load(raw_path, allow_pickle=False) as data:
        principal = np.linalg.eigvalsh(data['stress'].transpose(2, 0, 1))[:, 2]
        assert np.all(np.isfinite(principal))
        volume = data['volume']
        centers = data['p'][data['t']].mean(1)
        order = np.argsort(principal)[::-1]
        hot = order[0]
        assert np.all(volume > 0)
        npz_cells = len(principal)
    for key in ['relative_free_residual', 'relative_force_balance_error',
                'relative_moment_balance_error']:
        assert report[key] < 1e-6, (report_path, key)
    assert report['contact_converged']
    front = np.array(report['patches']['front_seat']['mean_displacement_mm_at_E1000'])
    rear = np.array(report['patches']['rear_seat']['mean_displacement_mm_at_E1000'])
    movement = float(max(np.linalg.norm(front), np.linalg.norm(rear)))
    ratio = 40.5/float(principal[hot])
    slice_path = cad_folder/'toolpath-verification.json'
    sliced = json.loads(slice_path.read_text()) if slice_path.exists() else {}
    mass = sliced.get('neutral_printed_mass_g')
    result = {
        'study': folder.name, 'mesh_h_mm': float(name.split('-h')[-1]),
        'raw_field': raw_path.relative_to(ROOT).as_posix(),
        'raw_field_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'nodes': report['nodes'], 'tetrahedra': npz_cells,
        'E_reference_MPa': 1000., 'load_reference_kg': 12.,
        'front_vertical_movement_mm': float(-front[1]),
        'front_translation_vector_mm': front.tolist(),
        'rear_translation_vector_mm': rear.tolist(),
        'maximum_seat_mean_translation_magnitude_mm': movement,
        'remaining_of_5mm_total_translation_budget_mm': 5.-movement,
        'proportional_1p25kg_spool_translation_proxy_mm': movement*1.25/12.,
        'movement_gate_with_provisional_1mm_rail_mount_reserve': movement <= 4.,
        'spool_increment_proxy_gate': movement*1.25/12. <= 1.,
        'raw_peak_tensile_MPa': float(principal[hot]),
        'raw_peak_center_mm': centers[hot].tolist(),
        'raw_peak_cell_volume_mm3': float(volume[hot]),
        'raw_peak_40p5MPa_coupon_strength_ratio': ratio,
        'passes_nominal_4x_fracture_screen': ratio >= 4.,
        'material_volume_above_10p125MPa_mm3': float(volume[principal > 10.125].sum()),
        'top_12_finite_tensile_cells': [
            {'tensile_MPa': float(principal[i]), 'center_mm': centers[i].tolist(),
             'volume_mm3': float(volume[i])} for i in order[:12]],
        'sliced_volume_cm3': sliced.get('printed_volume_cm3'),
        'sliced_mass_g_at_1p24': mass,
        'toolpath_status': sliced.get('status'),
        'load_compliance_Nmm_at_E1000': report.get('load_compliance_Nmm_at_E1000'),
        'reference_load_per_vertical_movement_per_gram_N_per_mm_g':
            117.72/(-float(front[1]))/mass if mass else None,
        'numerical_gates_pass': True,
        'physical_qualification': False,
        'limitations': 'Isotropic ideal printed-material model; zero sparse-infill stiffness. Seat translation is modeled, rail/mount reserve is provisional, and spool increment is proportional to the same load pattern. Coupon strength is not a tested part allowable. All finite stress cells retained.'}
    return result


def mechanics_summary():
    rows = []
    for study in ['seed1-best', 'full-plane-best', 'seat-support']:
        folder = D/'studies'/study
        for report in sorted(folder.glob('*-results.json')):
            rows.append(field_metrics(folder, report.name.removesuffix('-results.json'), CAD/'studies'/study))
    write('mechanics-summary.json', {'fields': rows,
          'strength_screen_MPa': 40.5/4,
          'fully_qualified_design_selected': False,
          'note': 'Any computational candidate selection also needs all remaining gates; no physical qualification is implied.'})
    return rows


if __name__ == '__main__':
    search = search_summary()
    mechanics = mechanics_summary()
    print('Unique search candidates:', search['unique_parameter_sets_all_runs'])
    for row in mechanics:
        print(row['study'], row['mesh_h_mm'], 'front', row['front_vertical_movement_mm'],
              'raw tensile', row['raw_peak_tensile_MPa'], 'ratio', row['raw_peak_40p5MPa_coupon_strength_ratio'])
