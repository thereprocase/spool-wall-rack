"""Preserve G geometry and helper placement; request zero base sparse infill."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
SOURCE = ROOT/'designs/rev-g'
OUT = D/'g-recheck'
CASES = {'2w-5layers': (2, 1.0), '8w-2layers': (8, .4),
         '2w-8layers': (2, 1.6), '2w-2layers': (2, .4), '8w-8layers': (8, 1.6)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', choices=list(CASES), required=True)
    args = parser.parse_args()
    out = OUT/args.case
    out.mkdir(parents=True, exist_ok=True)
    names = ['body-only', 'dense-chords-and-seats', 'rib-plane-lower', 'rib-plane-upper']
    copied = []
    for name in names:
        for suffix in ['.stl', '.step']:
            path = SOURCE/(name+suffix)
            shutil.copyfile(path, out/path.name)
            copied.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for name in ['body-mounted.stl', 'bracket-with-modifiers.step']:
        shutil.copyfile(SOURCE/name, out/name)
    params = json.loads((SOURCE/'selected-layout.json').read_text())
    assert params['walls'] == 1 and params['skin_mm'] == 1.0 and params['plane_mm'] == 1.0
    params['infill_percent'] = 0
    params['walls'], params['skin_mm'] = CASES[args.case]
    params['name'] = 'G finalist / material-model recheck / '+args.case
    (out/'selected-layout.json').write_text(json.dumps(params, indent=2)+'\n', encoding='utf-8')
    subprocess.run([sys.executable, str(SOURCE/'package_3mf.py'), str(out)], check=True)
    record = {'reference': 'Published G full-plane finalist 213f8c56151ddee40d51',
              'changes': ['Base sparse infill changed from 5% to 0%.',
                          f"{params['walls']} walls and {params['skin_mm']:g} mm top/bottom thickness."],
              'unchanged': ['Body geometry', 'Three helper geometries and locations',
                            '100% helper infill'],
              'copied_geometry': copied,
              'status': 'Prepared; slicing and corrected mechanics are separate checks.'}
    (out/'source-verification.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
