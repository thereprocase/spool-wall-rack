"""Verify the saved checkpoint without rerunning optimization or mechanics."""
from pathlib import Path
import hashlib
import json
import re
import zipfile
import numpy as np

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CAD = ROOT / 'designs/rev-f'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def published_files():
    paths = [ROOT / name for name in ['README.md', 'AGENTS.md',
             'DESIGN-JOURNAL.md', 'E13-ENGINEERING-GUIDE.md', 'NEXT-SPRINT.md']]
    for folder in [D, CAD]:
        paths.extend(p for p in folder.rglob('*') if p.is_file()
                     and not any(s in p.parts for s in ['.work', '__pycache__'])
                     and p.suffix != '.brep'
                     and not (p.parent == D and p.suffix == '.npz'
                              and not p.name.endswith('-solution.npz')))
    return sorted(set(paths))


def main():
    files = published_files()
    assert all(p.stat().st_size < 100 * 1024**2 for p in files)
    for path in files:
        if path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8'))
        if path.suffix == '.py':
            compile(path.read_bytes(), path.name, 'exec')
    links = 0
    for path in files:
        if path.suffix != '.md':
            continue
        for target in re.findall(r'\]\(([^)\s]+)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            dest = (path.parent / target.split('#')[0]).resolve()
            generated = [D / 'checkpoint-manifest.json', D / 'checkpoint-verification.json']
            assert dest.exists() or dest in generated, (str(path.relative_to(ROOT)), target)
            links += 1
    geometry = json.loads((CAD / 'geometry-verification.json').read_text())
    assert geometry['Rev_F_STEP_sha256'] == sha(CAD / 'body-only.step')
    assert geometry['E13_STEP_sha256'] == sha(ROOT / 'designs/closed-wall-e13/body-only.step')
    assert geometry['body_valid'] and geometry['body_solids'] == 1
    assert geometry['same_external_bounds'] and geometry['added_outside_E13_mm3'] < 1e-8
    assert all(x['unchanged'] for x in geometry['preserved_interfaces'])
    slices = []
    for folder in [CAD, CAD / 'studies/full-plane-4w']:
        audit = json.loads((folder / 'toolpath-verification.json').read_text())
        pack = json.loads((folder / '3mf-verification.json').read_text())
        actual_hash = sha(folder / 'rev-f-model-and-modifiers.3mf')
        assert actual_hash == pack['sha256'] == audit['input_3MF_sha256']
        assert sha(folder / 'body-only.step') == geometry['Rev_F_STEP_sha256']
        for part in pack['parts']:
            assert part['STL_sha256'] == sha(folder / (part['name'] + '.stl'))
        assert audit['layer_count'] == 120
        assert not audit['selection_tabs_printed']
        assert not audit['window_extrusion_centerlines_detected']
        assert [p['role'] for p in audit['roundtrip_parts']] == ['normal_part'] + ['modifier_part'] * 3
        assert max(p['maximum_roundtrip_vertex_error_mm'] for p in audit['roundtrip_parts']) < 0.0001
        assert audit['minimum_structural_coverage'] > .99
        assert audit['minimum_dense_helper_coverage'] > .98
        with zipfile.ZipFile(folder / 'rev-f-model-and-modifiers.3mf') as z:
            assert len(z.namelist()) == 4
            assert not any('gcode' in n.lower() or 'project_settings' in n for n in z.namelist())
        slices.append({'candidate': audit['parameters']['name'],
                       'printed_volume_cm3': audit['printed_volume_cm3'],
                       'neutral_mass_g': audit['neutral_printed_mass_g'],
                       'geometry_package_matches_completed_audit': True})
    metrics = json.loads((D / 'checkpoint-metrics.json').read_text())
    for row in metrics['fields']:
        field_path = ROOT / row['field']
        assert sha(field_path) == row['field_sha256']
        with np.load(field_path, allow_pickle=False) as data:
            principal = np.linalg.eigvalsh(data['stress'].transpose(2, 0, 1))[:, 2]
            assert np.all(np.isfinite(principal)) and np.all(data['volume'] > 0)
            assert len(principal) == row['tetrahedra']
            assert abs(float(principal.max()) - row['max_principal_MPa_all_finite_cells']) < 1e-8
            assert abs(40.5 / float(principal.max()) - row['conservative_40p5MPa_strength_ratio']) < 1e-10
            assert row['passes_requested_4x_screen'] == bool(principal.max() <= 10.125)
        assert all(row[key] < 1e-6 for key in ['relative_free_residual',
                   'relative_force_balance_error', 'relative_moment_balance_error'])
    outlines = json.loads((D / 'inputs/e13-layer-outlines.json').read_text())
    assert outlines['stl_sha256'] == sha(ROOT / 'designs/closed-wall-e13/body-mounted.stl')
    assert len(outlines['wkb_hex']) == 120
    report = {'status': 'PASS: checkpoint integrity, not design qualification',
              'python_sources_compile': True, 'JSON_parses': True,
              'local_document_links_checked': links,
              'body_and_protected_interface_evidence_matches': True,
              'sliced_candidates': slices, 'unfiltered_3D_fields_checked': len(metrics['fields']),
              'all_independent_equilibrium_gates_below_1e_6': True,
              'candidates_passing_requested_4x_3D_screen': 0,
              'light_candidate_sliced': False, 'genetic_optimizer_started': False}
    save(D / 'checkpoint-verification.json', report)
    manifest = []
    for p in published_files():
        if p.name == 'checkpoint-manifest.json':
            continue
        is_text = p.suffix in ['.py', '.json', '.md', '.txt']
        content = p.read_text(encoding='utf-8').encode('utf-8') if is_text else p.read_bytes()
        manifest.append({'path': str(p.relative_to(ROOT)).replace('\\', '/'),
                         'bytes_in_hashed_representation': len(content),
                         'representation': 'LF-normalized UTF-8' if is_text else 'exact file bytes',
                         'sha256': hashlib.sha256(content).hexdigest()})
    save(D / 'checkpoint-manifest.json', {'files': manifest,
         'note': 'Published Rev F evidence and checkpoint documents; generated meshes/caches omitted. No optimization or solve rerun.'})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
