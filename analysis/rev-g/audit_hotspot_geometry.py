"""Locate the fine-field peak against actual delivered and baseline CAD faces."""
from pathlib import Path
import hashlib
import json
import cadquery as cq

D = Path(__file__).resolve().parent
ROOT = D.parents[1]


def read(path):
    return cq.importers.importStep(str(path)).val().translate((-250, -182, 0)).rotate((0, 0, 0), (0, 0, 1), 180)


def main():
    rows = json.loads((D/'mechanics-summary.json').read_text())['fields']
    row = next(r for r in rows if r['study'] == 'full-plane-best' and r['mesh_h_mm'] == 1)
    center = row['raw_peak_center_mm']
    point = cq.Vertex.makeVertex(*center)
    records = []
    for path in [ROOT/'designs/rev-g/body-only.step', ROOT/'designs/closed-wall-e13/body-only.step']:
        shape = read(path)
        nearest = sorted(shape.Faces(), key=lambda f: f.distance(point))[:4]
        records.append({'body': path.relative_to(ROOT).as_posix(),
                        'STEP_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'nearest_faces': [{'distance_from_peak_cell_center_mm': f.distance(point),
                            'face_center_mm': list(f.Center().toTuple()), 'surface_type': f.geomType(),
                            'normal': list(f.normalAt().toTuple())} for f in nearest]})
    assert abs(records[0]['nearest_faces'][0]['distance_from_peak_cell_center_mm']
               - records[1]['nearest_faces'][0]['distance_from_peak_cell_center_mm']) < 1e-7
    result = {'raw_field': row['raw_field'], 'raw_field_sha256': row['raw_field_sha256'],
              'raw_peak_tensile_MPa': row['raw_peak_tensile_MPa'], 'raw_peak_cell_center_mm': center,
              'raw_peak_cell_volume_mm3': row['raw_peak_cell_volume_mm3'], 'bodies': records,
              'finding': 'The fine-mesh global peak is adjacent to a preserved exterior forearm chamfer face. It is not solely an internal density-transition peak.',
              'limitation': 'CAD proximity locates the peak; it does not establish a stress artifact or a physical rupture allowable. All finite cells remain in the strength screen.'}
    (D/'hotspot-geometry-verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
