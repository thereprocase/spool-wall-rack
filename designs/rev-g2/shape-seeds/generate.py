"""Reproducible broad XY architecture sketches; no CAD or mechanics claims."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import textwrap

import numpy as np
from shapely import union_all
from shapely.geometry import LineString, Point, Polygon, box, mapping
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT / 'designs/rev-g'))
import layout

spec = importlib.util.spec_from_file_location('envelope', ROOT / 'designs/design-envelope/build_envelope.py')
envelope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(envelope)


def beam(points, width):
    return LineString(points).buffer(width / 2, quad_segs=8)


def curve(points, width):
    a, b, c = np.asarray(points, dtype=float)
    t = np.linspace(0, 1, 65)[:, None]
    return beam((1-t)**2*a + 2*t*(1-t)*b + t*t*c, width)


def definitions():
    return [
        dict(id='B-open-truss', title='B / Open triangular frame',
             reason='Separate upper and lower chords; remove broad low-load panels.',
             paths=[([(8, 32), (86, -18), (190, -7)], 8),
                    ([(8, -26), (90, -46), (190, -7)], 8),
                    ([(86, -18), (90, -46)], 6),
                    ([(135, -32), (136, -12)], 6)],
             section='24 mm-wide open web; dense chords; no mandatory internal plates'),
        dict(id='C-curved-braces', title='C / Curved twin braces',
             reason='Continuous curved seat-to-root paths with a large central opening.',
             paths=[([(86, -18), (190, -7)], 6)],
             curves=[([(8, 58), (28, -36), (86, -18)], 12),
                     ([(8, -26), (104, -65), (190, -7)], 10)],
             section='Open curved members across Z; compare solid and hollow member cores'),
        dict(id='E-deep-keel', title='E / Deep keel and seat struts',
             reason='Spend depth on chord separation, then cut the material between chords.',
             paths=[([(8, -27), (65, -53), (121, -47), (193, -9)], 9),
                    ([(8, 41), (83, -21)], 10),
                    ([(84, -16), (83, -51)], 9),
                    ([(84, -19), (189, -6)], 7),
                    ([(134, -40), (146, -11)], 7)],
             section='Deeper open cradle; depth shown is an exploration parameter, not an approved limit'),
        dict(id='D-independent-arms', title='D / Two direct seat arms',
             reason='Give each seat a direct wall-root path; separate the inner and outer branches.',
             paths=[([(8, 40), (85, -19)], 17),
                    ([(8, -25), (120, -37), (190, -8)], 15),
                    ([(85, -19), (100, -36)], 5)],
             section='Forked arms; through-width face coupling remains a 3D design variable'),
        dict(id='F-seat-portals', title='F / Broad seat portals',
             reason='Back each seat with a broad shoulder and rounded window, avoiding a thin neck.',
             paths=[([(8, 45), (77, -19), (107, -25), (174, -9), (192, -7)], 18),
                    ([(8, -26), (80, -43), (133, -35), (191, -8)], 12),
                    ([(82, -18), (81, -42)], 13)],
             section='Thick root transitions; varied windows and independent seat backing'),
        dict(id='A-shear-panels', title='A / Reshaped shear panels',
             reason='Broader outer plates follow a new lower contour; generous windows remove area.',
             polygon=[(0, -32), (8, 57), (82, -16), (108, -20),
                      (190, -4), (197, -14), (131, -40), (77, -48)],
             holes=[[(17, -21), (24, 23), (65, -15), (66, -32)],
                    [(109, -27), (145, -18), (167, -17), (132, -32)]],
             section='Outer skins with variable internal plates or local cross-width diaphragms'),
    ]


def build_seeds():
    params = json.loads((ROOT / 'designs/rev-g/selected-layout.json').read_text())
    reference = layout.outline().difference(layout.windows(params))
    contract = json.loads((ROOT / 'designs/design-envelope/definition.json').read_text())
    # Reuse only the proven continuous spool-sweep construction. The old frame
    # and its local underside restriction are not the new search boundary.
    _, _, _, _, spool, rods, _, _ = envelope.build(contract)
    fixed_seats = reference.intersection(union_all([
        Point(90, 0).buffer(21, quad_segs=64),
        Point(190, 12).buffer(21, quad_segs=64)]))
    wall = reference.intersection(box(0, -32, 12, 176))
    common = union_all([wall, fixed_seats])
    generated = []
    for seed in definitions():
        regions = [common]
        regions += [beam(points, width) for points, width in seed.get('paths', [])]
        regions += [curve(points, width) for points, width in seed.get('curves', [])]
        if 'polygon' in seed:
            panel = Polygon(seed['polygon'])
            for hole in seed['holes']:
                panel = panel.difference(Polygon(hole).buffer(-2).buffer(2))
            regions.append(panel)
        shape = union_all(regions).intersection(box(0, -100, 250, 180))
        # Preserve the reference seat and snap outlines as complete local
        # islands, including their entry gaps. New webs cannot fill those gaps.
        seat_masks = union_all([Point(90, 0).buffer(19.8, quad_segs=64),
                                Point(190, 12).buffer(19.8, quad_segs=64)])
        shape = shape.difference(seat_masks).union(reference.intersection(seat_masks))
        shape = shape.difference(spool).difference(rods).buffer(0)
        assert shape.is_valid and shape.geom_type == 'Polygon', (seed['id'], shape.geom_type)
        assert shape.intersection(spool).area < 1e-7
        assert shape.intersection(rods).area < 1e-7
        changes = dict(added_projection_mm2=float(shape.difference(reference).area),
                       removed_projection_mm2=float(reference.difference(shape).area))
        assert min(changes.values()) > 50, (seed['id'], changes)
        clearance = []
        for diameter in np.linspace(180, 220, 161):
            for radius in [12.4, 12.7]:
                q = np.sqrt((diameter / 2 + radius)**2 - 10144 / 4)
                center = Point(140 - 12*q/np.sqrt(10144), 6 + 100*q/np.sqrt(10144))
                clearance.append(shape.distance(center) - diameter / 2)
        assert min(clearance) >= 3.5
        seed.update(changes, projected_body_area_mm2=float(shape.area),
                    bounds_XY_mm=list(shape.bounds),
                    minimum_sampled_nominal_spool_clearance_mm=float(min(clearance)),
                    projected_connected_components=1, CAD_built=False,
                    mechanical_result=False, dimensional_envelope_confirmed=False)
        generated.append((seed, shape))
    return reference, spool, rods, generated


def render(reference, spool, rods, generated):
    fig, axes = plt.subplots(2, 3, figsize=(16, 10.5), facecolor='#f4f2ed', layout='constrained')
    for ax, (seed, shape) in zip(axes.flat, generated):
        ax.set_facecolor('#f4f2ed')
        envelope.draw(ax, spool.intersection(box(0, -65, 223, 180)), '#e2e3e0', edgecolor='none')
        envelope.draw(ax, reference, 'none', edgecolor='#a5a7a4', linewidth=1.0, linestyle='--')
        envelope.draw(ax, shape, '#347c81', edgecolor='#194a50', linewidth=.65)
        envelope.draw(ax, rods, '#d8b268', edgecolor='#94722e', linewidth=.7)
        for y in [40, 164]:
            ax.plot(3.6, y, 'o', color='#dc6b45', markersize=4)
        ax.plot([0, 0], [-32, 176], color='#243f42', lw=1)
        ax.set(aspect='equal', xlim=(-7, 225), ylim=(-66, 185), title=seed['title'])
        ax.set_xlabel('Projection from wall (mm)', fontsize=8)
        ax.set_ylabel('Height relative to rear rod (mm)', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        ax.text(.04, .975, 'CONCEPT / UNBUILT', transform=ax.transAxes, va='top', fontsize=7, color='#68726d')
        ax.text(.53, .64, textwrap.fill(seed['reason'], width=44),
                transform=ax.transAxes, ha='center', va='center', fontsize=8, wrap=True)
    fig.suptitle('G2 / change the structure, including the outside shape', fontsize=20, fontweight='bold', color='#243f42')
    fig.supxlabel('Teal: candidate body projection · dashed: G reference · gold: fixed rods · orange: fixed mounting axes · gray: spool exclusion\nSix reproducible geometry sketches. Bottom-corner and 15 mm outboard datums await clarification; the depth shown is provisional. No CAD, sliced mass or strength ranking is implied.', fontsize=10)
    fig.savefig(D / 'architecture-directions.png', dpi=160)
    plt.close(fig)
    for seed, shape in generated:
        fig, ax = plt.subplots(figsize=(7, 7), facecolor='#f4f2ed', layout='constrained')
        ax.set_facecolor('#f4f2ed')
        envelope.draw(ax, reference, 'none', edgecolor='#a5a7a4', linewidth=1, linestyle='--')
        envelope.draw(ax, shape, '#347c81', edgecolor='#194a50', linewidth=.7)
        envelope.draw(ax, rods, '#d8b268', edgecolor='#94722e', linewidth=.7)
        ax.set(aspect='equal', xlim=(-7, 225), ylim=(-66, 185), title=seed['title'])
        ax.set_xlabel('Projection from wall (mm)'); ax.set_ylabel('Height relative to rear rod (mm)')
        fig.supxlabel('Unbuilt geometry sketch. Envelope datums and 3D function remain to be checked.', fontsize=9)
        fig.savefig(D / (seed['id'] + '.png'), dpi=140); plt.close(fig)


def main():
    reference, spool, rods, generated = build_seeds()
    render(reference, spool, rods, generated)
    features = [dict(type='Feature', properties=seed, geometry=mapping(shape)) for seed, shape in generated]
    (D / 'seeds.geojson').write_text(json.dumps(dict(type='FeatureCollection', features=features), separators=(',', ':'))+'\n')
    record = dict(status='SIX_CONNECTED_XY_CONCEPTS; CAD_AND_MECHANICS_UNBUILT',
                  source_sha256=hashlib.sha256(Path(__file__).read_text().encode()).hexdigest(),
                  source_inputs_sha256={p: hashlib.sha256((ROOT/p).read_text().encode()).hexdigest()
                                        for p in ['designs/rev-g/layout.py',
                                                  'designs/rev-g/selected-layout.json',
                                                  'designs/closed-wall-e13/profile.svg',
                                                  'designs/design-envelope/definition.json',
                                                  'designs/design-envelope/build_envelope.py']},
                  text_hash_representation='UTF-8 with normalized LF line endings',
                  fixed_rod_centers_XY_mm=[[90, 0], [190, 12]],
                  fixed_mounting_axes_YZ_mm=[[164, 12], [40, 12]],
                  nominal_spool_diameter_range_mm=[180, 220],
                  minimum_nominal_spool_clearance_mm=3.5,
                  envelope_anchors_pending=['Exact bottom corner datum', 'Datum for 15 mm outboard'],
                  preview_only_width_Z_mm=24,
                  old_local_underside_floor_enforced=False,
                  generated=[seed for seed, shape in generated])
    (D / 'verification.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'generated'}), flush=True)


if __name__ == '__main__':
    main()
