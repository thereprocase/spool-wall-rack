"""Audit Rev G publication provenance and retained failures without new solves."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import zipfile
import numpy as np
from fast_screen import source_hash
import search
import layout

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CAD = ROOT/'designs/rev-g'
TEXT_SUFFIXES = {'.py', '.json', '.md', '.txt', '.svg'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def published_files():
    files = [ROOT/n for n in ['README.md', 'AGENTS.md', 'DESIGN-JOURNAL.md',
             'NEXT-SPRINT.md', 'REV-F-CHECKPOINT.md', 'REV-G-SPRINT-BRIEF.md',
             '.gitignore', '.gitattributes']]
    for directory in [D, CAD]:
        files.extend(p for p in directory.rglob('*') if p.is_file()
                     and not any(s in p.parts for s in ['.work', '__pycache__'])
                     and p.suffix not in {'.brep', '.log'})
    return sorted(set(files))


def search_audit():
    validation = read(D/'fast-screen-validation.json')
    assert validation['status'] == 'PASS' and validation['source_hash'] == source_hash()
    assert len(validation['cases']) == 4
    assert all(r['uncached_repeat_matches'] and r['maximum_displacement_error_mm'] < 1e-8
               and r['maximum_stress_component_error_MPa'] < 1e-8 for r in validation['cases'])
    broad = {'signature': search.search_signature(2.), 'genes': copy.deepcopy(search.GENES),
             'screen_limits': copy.deepcopy(search.LIMITS), 'fixed': copy.deepcopy(search.FIXED)}
    import search_3d_feedback  # Select the independently recorded second family.
    feedback = {'signature': search.search_signature(2.), 'genes': copy.deepcopy(search.GENES),
                'screen_limits': copy.deepcopy(search.LIMITS), 'fixed': copy.deepcopy(search.FIXED)}
    definitions = {r['signature']: r for r in [broad, feedback]}
    save(D/'search-definitions.json', {'broad_family': broad, 'feedback_family': feedback})
    union, runs = {}, []
    for folder in sorted((D/'runs').iterdir()):
        run = read(folder/'summary.json'); definition = definitions[run['search_signature']]
        records = {}
        for ident in run['evaluated_candidate_ids']:
            row = read(D/'search-evidence'/run['search_signature'][:16]/f'candidate-{ident}.json')
            assert row['search_signature'] == run['search_signature']
            assert hashlib.sha256(search.canonical(row['parameters']).encode()).hexdigest()[:20] == ident
            decoded = {**definition['fixed'], **{key: choices[g] for (key, choices), g
                       in zip(definition['genes'].items(), row['genome'])}}
            assert decoded == row['parameters']
            records[ident] = row; union[ident] = row
        ledger = read(folder/'generations.json')
        assert hashlib.sha256(search.canonical(ledger).encode()).hexdigest() == run['generation_ledger_sha256']
        for generation in ledger:
            best = min((records[i] for i in generation['population']), key=lambda r: (r['score'], r['id']))
            assert best['id'] == generation['best_id'] and best['score'] == generation['best_score']
        assert min(records.values(), key=lambda r: (r['score'], r['id'])) == run['best_candidate']
        runs.append({'run': folder.name, 'signature_matches_current_sources': True,
                     'candidates': len(records), 'ledger_hash_matches': True})
    repeat = read(D/'repeatability-verification.json')
    assert repeat['status'] == 'PASS'
    for row in repeat['replays']:
        for name in ['summary.json', 'generations.json']:
            assert read(D/'runs'/row['original_run']/name) == read(D/'runs'/row['repeat_run']/name)
    assert len(union) == read(D/'search-summary.json')['unique_parameter_sets_all_runs'] == 1458
    return {'unique_parameter_sets': len(union), 'runs': runs, 'exact_cached_replays': len(repeat['replays']),
            'canonical_uncached_cases': 4}


def slice_audit(require_local):
    rows = []
    for study in ['seed1-best', 'full-plane-best', 'seat-support', 'repaired-f-light']:
        folder = CAD/'studies'/study
        audit = read(folder/'toolpath-verification.json'); pack = read(folder/'3mf-verification.json')
        params = read(folder/'selected-layout.json'); helpers = read(folder/'helper-verification.json')
        assert audit['parameters'] == params
        assert helpers['layout_sha256'] == layout.layout_hash(params)
        assert helpers['delivered_STEP_solids'] == 4
        assert all(r['valid'] and r['solid_count'] == 1 and r['tab_body_intersection_mm3'] == 0 for r in helpers['parts'])
        assert sha(folder/'rev-g-model-and-modifiers.3mf') == pack['sha256'] == audit['input_3MF_sha256']
        for part in pack['parts']:
            assert sha(folder/(part['name']+'.stl')) == part['STL_sha256']
        assert audit['layer_count'] == 120
        assert not audit['selection_tabs_printed'] and not audit['window_extrusion_centerlines_detected']
        assert [r['role'] for r in audit['roundtrip_parts']] == ['normal_part']+['modifier_part']*3
        assert max(r['maximum_roundtrip_vertex_error_mm'] for r in audit['roundtrip_parts']) < .0001
        passes = audit['minimum_structural_coverage'] > .96 and audit['minimum_dense_helper_coverage'] > .985
        assert audit.get('passes_coverage_gates', passes) == passes
        if study == 'seed1-best':
            assert not passes and audit['minimum_dense_helper_coverage'] < .985
        else:
            assert passes and audit['minimum_structural_coverage'] > .96
            assert audit['minimum_dense_helper_coverage'] > .985
        with zipfile.ZipFile(folder/'rev-g-model-and-modifiers.3mf') as archive:
            assert len(archive.namelist()) == 4
            assert not any('gcode' in n.lower() or 'project_settings' in n for n in archive.namelist())
        gcode = folder/'.work'/f"audit-{params['walls']}w"/'plate_1.gcode'
        if study == 'repaired-f-light' and not gcode.exists():
            # This first G audit ran at the root before its immutable study copy.
            gcode = CAD/'.work'/f"audit-{params['walls']}w"/'plate_1.gcode'
        if require_local:
            assert gcode.exists(), gcode
        if gcode.exists():
            assert sha(gcode) == audit['gcode_sha256']
        rows.append({'study': study, 'actual_mass_g': audit['neutral_printed_mass_g'],
                     'toolpath_status': audit.get('status', 'PASS' if passes else 'FAIL: nominal footprint coverage'), 'input_bindings_match': True,
                     'local_Gcode_hash_checked': gcode.exists()})
    # The top-level research package is exactly the completed full-plane slice.
    for name in ['body-only.step', 'body-only.stl', 'bracket-with-modifiers.step',
                 'rev-g-model-and-modifiers.3mf', 'toolpath-verification.json']:
        assert sha(CAD/name) == sha(CAD/'studies/full-plane-best'/name)
    protected = read(CAD/'geometry-verification.json')
    assert protected['Rev_G_STEP_sha256'] == sha(CAD/'body-only.step')
    assert protected['E13_STEP_sha256'] == sha(ROOT/'designs/closed-wall-e13/body-only.step')
    assert protected['body_valid'] and protected['body_solids'] == 1 and protected['same_external_bounds']
    assert all(r['unchanged'] for r in protected['preserved_interfaces'])
    assert abs(protected['window_chamfer_min_deg']-50) < 1e-5
    assert abs(protected['window_chamfer_max_deg']-50) < 1e-5
    assert sha(CAD/'studies/seat-support/body-only.step') == protected['Rev_G_STEP_sha256']
    # The two window-scale-1 studies retain the already audited F body.
    for study in ['seed1-best', 'repaired-f-light']:
        assert sha(CAD/'studies'/study/'body-only.step') == sha(ROOT/'designs/rev-f/body-only.step')
    return rows


def mechanics_audit():
    summary = read(D/'mechanics-summary.json'); rows = []
    for row in summary['fields']:
        path = ROOT/row['raw_field']; assert sha(path) == row['raw_field_sha256']
        with np.load(path, allow_pickle=False) as data:
            stress = np.linalg.eigvalsh(data['stress'].transpose(2, 0, 1))[:, 2]
            assert np.all(np.isfinite(stress)) and np.all(data['volume'] > 0)
            assert len(stress) == row['tetrahedra']
            assert abs(stress.max()-row['raw_peak_tensile_MPa']) < 1e-8
            assert abs(40.5/stress.max()-row['raw_peak_40p5MPa_coupon_strength_ratio']) < 1e-10
            assert abs(data['volume'][stress > 10.125].sum()-row['material_volume_above_10p125MPa_mm3']) < 1e-8
        assert row['passes_nominal_4x_fracture_screen'] == bool(stress.max() <= 10.125)
        report = read(path.with_name(path.name.replace('-solution.npz', '-results.json')))
        mesh = read(path.with_name(path.name.replace('-solution.npz', '-mesh-quality.json')))
        assert report['contact_converged']
        assert all(report[k] < 1e-6 for k in ['relative_free_residual', 'relative_force_balance_error', 'relative_moment_balance_error'])
        assert mesh['removed_absolute_volume_mm3'] < 1e-8
        geometry = read(path.parent/'geometry-1w.json')
        assert geometry['body_STEP_sha256'] == sha(CAD/'studies'/row['study']/'body-only.step')
        assert geometry['layout_sha256'] == layout.layout_hash(geometry['parameters'])
        rows.append({'study': row['study'], 'h': row['mesh_h_mm'], 'raw_field_hash_matches': True,
                     'all_finite_cells_checked': len(stress), 'equilibrium_gates_pass': True,
                     'passes_nominal_4x_fracture_screen': row['passes_nominal_4x_fracture_screen']})
    assert len(rows) == 5 and not any(r['passes_nominal_4x_fracture_screen'] for r in rows)
    hotspot = read(D/'hotspot-geometry-verification.json')
    assert sha(ROOT/hotspot['raw_field']) == hotspot['raw_field_sha256']
    for r in hotspot['bodies']:
        assert sha(ROOT/r['body']) == r['STEP_sha256']
    return rows


def buckling_audit():
    validation = read(D/'buckling-validation.json'); assert validation['status'] == 'PASS'
    rows = []
    for study, orders in [('repaired-f-light', [1, 2]), ('full-plane-best', [2])]:
        source = (ROOT/'analysis/rev-f/studies/light-full-1w/print-material-1w-h2-solution.npz'
                  if study == 'repaired-f-light' else D/'studies/full-plane-best/print-material-1w-h2-solution.npz')
        for order in orders:
            prefix = D/'studies'/study/f'buckling-p{order}-h2'; result = read(prefix.with_suffix('.json'))
            assert result['source_sha256'] == sha(source) and result['element_order'] == order
            assert all(r['relative_eigen_residual'] < 1e-5 for r in result['modes'])
            with np.load(prefix.with_suffix('.npz'), allow_pickle=False) as data, np.load(source, allow_pickle=False) as static:
                assert np.array_equal(data['p'], static['p']) and np.array_equal(data['t'], static['t'])
                assert np.all(np.isfinite(data['modes'])) and data['modes'].shape[2] == 6
            rows.append({'study': study, 'order': order, 'source_field_matches': True,
                         'eigen_residual_gate_pass': True, 'first_multiplier': result['lowest_positive_multiplier']})
    return rows


def main(require_local):
    search_result = search_audit()
    slices = slice_audit(require_local)
    mechanics = mechanics_audit()
    buckling = buckling_audit()
    files = published_files(); links = 0
    generated = [D/'publication-manifest.json', D/'publication-verification.json']
    for path in files:
        assert path.stat().st_size < 100*1024**2, path
        if path.suffix == '.json': read(path)
        if path.suffix == '.py': compile(path.read_bytes(), path.name, 'exec')
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)\s]+)', path.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'): continue
                dest = (path.parent/target.split('#')[0]).resolve()
                assert dest.exists() or dest in generated, (path.relative_to(ROOT), target)
                links += 1
    report = {'status': 'PASS: publication integrity; no qualified design selected',
              'search': search_result, 'sliced_candidates': slices, 'raw_3D_fields': mechanics,
              'buckling_fields': buckling, 'local_document_links_checked': links,
              'protected_interfaces_match_delivered_CAD': True,
              'python_sources_compile': True, 'all_JSON_parses': True,
              'genetic_search_sprint_complete': True, 'physically_qualified_design_selected': False,
              'computationally_accepted_finalist_selected': False}
    save(D/'publication-verification.json', report)
    manifest = []
    for path in published_files():
        if path.name == 'publication-manifest.json': continue
        text = path.suffix in TEXT_SUFFIXES or path.name in ['.gitignore', '.gitattributes']
        content = path.read_text(encoding='utf-8').encode('utf-8') if text else path.read_bytes()
        manifest.append({'path': path.relative_to(ROOT).as_posix(), 'bytes_in_hashed_representation': len(content),
                         'representation': 'LF-normalized UTF-8' if text else 'exact file bytes',
                         'sha256': hashlib.sha256(content).hexdigest()})
    save(D/'publication-manifest.json', {'files': manifest,
         'note': 'Rev G source, candidate ledger, CAD, finite fields and reports. Regenerable caches and neutral G-code excluded. Integrity is not physical qualification.'})
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--require-local-slices', action='store_true')
    main(parser.parse_args().require_local_slices)
