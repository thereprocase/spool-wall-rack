"""Comment-dialect regression and fresh P1S/PETG process audit."""
from pathlib import Path
import argparse
import json
import shutil
import tempfile

import numpy as np

from plastic_shape import read_paths
from audit_process_matrix import parse_gcode,model_settings_summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fresh',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    original = Path('designs/rev-g2/g-recheck/2w-5layers/.work/audit-2w')
    before,original_report = read_paths(original)
    source = (original/'plate_1.gcode').read_text()
    for a,b in [(';TYPE:','; FEATURE: '),(';WIDTH:','; LINE_WIDTH: '),
                (';HEIGHT:','; LAYER_HEIGHT: '),(';Z:','; Z_HEIGHT: ')]:
        source = source.replace(a,b)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        (folder/'plate_1.gcode').write_text(source)
        shutil.copyfile(original/'audit.3mf',folder/'audit.3mf')
        converted,_ = read_paths(folder)
        assert all(np.array_equal(before[k],converted[k]) for k in before)
        audit_old,_ = parse_gcode(original/'plate_1.gcode')
        audit_converted,_ = parse_gcode(folder/'plate_1.gcode')
        assert len(audit_old) == len(audit_converted)
        for key in ['width','height','z','role','e']:
            assert [r[key] for r in audit_old] == [r[key] for r in audit_converted]
    with np.load('analysis/rev-g2/g-recheck/2w-5layers/validated-shape/extrusion-paths.npz') as cached:
        matches = {key:bool(np.array_equal(before[key],cached[key])) for key in before}
    assert all(matches.values()),matches
    data,accounting = read_paths(args.fresh)
    rows,_ = parse_gcode(args.fresh/'plate_1.gcode')
    assert len(rows) == len(data['paths'])
    assert np.allclose([r['width'] for r in rows],data['width'],rtol=0,atol=0)
    assert np.array_equal([r['role'] for r in rows],data['role'])
    xy = np.array([[r['a'][:2],r['b'][:2]] for r in rows])
    width = np.array([r['width'] for r in rows])
    lower,upper = xy.min(axis=1)-width[:,None]/2,xy.max(axis=1)+width[:,None]/2
    outside = np.any(lower < 0,axis=1)|np.any(upper > 256,axis=1)
    excluded = (lower[:,0] < 18)&(upper[:,0] > 0)&(lower[:,1] < 28)&(upper[:,1] > 0)
    assert not outside.any() and not excluded.any()
    model = model_settings_summary(args.fresh/'audit.3mf')
    helpers = [part for part in model['parts'] if part.get('subtype') == 'modifier_part']
    assert len(helpers) == 3 and all(part.get('sparse_infill_density') == '100%' for part in helpers)
    report = {'status':'PASS_COMMENT_DIALECT_AND_PROCESS_AUDIT',
              'legacy_arrays_match_preserved_cache':matches,
              'transformed_comment_dialect_arrays_match':True,
              'independent_parser_width_and_role_match':True,
              'fresh_object_extrusion_segments':len(rows),'helper_regions':len(helpers),
              'helper_infill_density':'100%','outside_P1S_bed_segments':int(outside.sum()),
              'P1S_exclusion_intersections':int(excluded.sum()),
              'fresh_accounting':accounting,
              'fresh_shape_cache_gate':'PASS' if accounting['relative_extrusion_footer_difference'] < .001 else 'FAIL_FOOTER_RECONCILIATION',
              'scope':'Bambu comment support preserves old parsed data exactly. Process audit does not waive the existing extrusion/footer accounting gate.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__ == '__main__':
    main()
