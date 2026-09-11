"""E's deep frame with F-derived seat backing and G's installation datums."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from shapely import union_all
from shapely.geometry import Point, box, shape, mapping, LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(D.parent / 'shape-seeds'))
import generate as seeds


def main():
    seed_path = D.parent / 'shape-seeds/seeds.geojson'
    source = json.loads(seed_path.read_text())
    shapes = {v['properties']['id']: shape(v['geometry']) for v in source['features']}
    e, f = shapes['E-deep-keel'], shapes['F-seat-portals']
    influence = union_all([Point(90, 0).buffer(34, quad_segs=32),
                           Point(190, 12).buffer(30, quad_segs=32)])
    hybrid = e.union(f.intersection(influence)).buffer(1.25, quad_segs=12).buffer(-1.25, quad_segs=12)
    reference = seeds.layout.outline().difference(seeds.layout.windows({'window_scale': .9}))
    # Preserve the bearing bore and upper capture features. Outside the lower
    # 17 mm radius, the new roots may back the seat through the full width.
    protection = union_all([Point(x, y).buffer(17, quad_segs=64).union(
        Point(x, y).buffer(19.8, quad_segs=64).intersection(box(x-21, y-3, x+21, y+22)))
        for x, y in [(90, 0), (190, 12)]])
    hybrid = hybrid.difference(protection).union(reference.intersection(protection))
    contract = json.loads((ROOT / 'designs/design-envelope/definition.json').read_text())
    _, _, _, _, spool, rods, _, _ = seeds.envelope.build(contract)
    hybrid = hybrid.difference(spool).difference(rods).difference(seeds.moulding_keepout()).intersection(box(0, -100, 250, 180))
    # This approximation is only for the new extruded members. Actual G STEP
    # geometry replaces the protected interface volumes during CAD construction.
    hybrid = hybrid.simplify(.005, preserve_topology=True)
    # Reapply the locating surface after smoothing/simplification so the
    # physical installation datum cannot be rounded away at the wall corner.
    hybrid = hybrid.union(box(0, -32, 25.4, -22))
    assert hybrid.is_valid and hybrid.geom_type == 'Polygon'
    assert hybrid.intersection(seeds.moulding_keepout()).area < 1e-7
    lip = LineString([(0, -32), (25.4, -32)])
    assert hybrid.boundary.intersection(lip).length >= 25.4-1e-6
    clearance = []
    for diameter in np.linspace(180, 220, 161):
        for radius in [12.4, 12.7]:
            q = np.sqrt((diameter/2+radius)**2 - 10144/4)
            center = Point(140-12*q/np.sqrt(10144), 6+100*q/np.sqrt(10144))
            clearance.append(hybrid.distance(center)-diameter/2)
    assert min(clearance) > 3.5
    geometry = dict(type='FeatureCollection', features=[
        dict(type='Feature', properties=dict(name=name), geometry=mapping(p))
        for name, p in [('hybrid_body_projection', hybrid), ('protected_G_interfaces', protection)]])
    (D / 'geometry.geojson').write_text(json.dumps(geometry, separators=(',', ':'))+'\n')
    params = dict(name='EF deep frame with backed seat roots', walls=2, infill_percent=0,
                  skin_mm=1.0, plane_mm=1.0, planes='full', bottom_band=1.8,
                  diagonal_band=1.8, seat_band=5.5, front_seat_band=3.0,
                  lower_tunnel_collar_mm=3.5, upper_tunnel_collar_mm=2.5, window_scale=0)
    (D / 'selected-layout.json').write_text(json.dumps(params, indent=2)+'\n')
    record = dict(status='PASS_XY_GEOMETRY; CAD_AND_SLICING_REQUIRED',
                  fixed_rod_centers_XY_mm=[[90, 0], [190, 12]],
                  fixed_mounting_axes_YZ_mm=[[164, 12], [40, 12]],
                  moulding_clearance=seeds.moulding_definition(),
                  projected_connected_components=1, projected_body_area_mm2=hybrid.area,
                  area_added_to_E_mm2=hybrid.difference(e).area,
                  area_removed_from_E_mm2=e.difference(hybrid).area,
                  minimum_sampled_nominal_spool_clearance_mm=min(clearance),
                  moulding_overlap_mm2=hybrid.intersection(seeds.moulding_keepout()).area,
                  matching_locating_edge_mm=hybrid.boundary.intersection(lip).length,
                  bounds_XY_mm=list(hybrid.bounds),
                  source_text_hashes={p: hashlib.sha256((ROOT/p).read_text().encode()).hexdigest()
                                     for p in ['designs/rev-g2/shape-seeds/seeds.geojson',
                                               'designs/rev-g2/shape-seeds/moulding-clearance.json',
                                               'designs/rev-g2/ef-hybrid-v1/prepare.py']},
                  note='Projected area is not printed mass. Moulding is a locating datum, with no assumed structural support.')
    (D / 'projection-verification.json').write_text(json.dumps(record, indent=2)+'\n')
    fig, (ax, zoom) = plt.subplots(1, 2, figsize=(13, 7), facecolor='#f4f2ed', layout='constrained', gridspec_kw={'width_ratios': [1, 1.2]})
    for a in [ax, zoom]:
        a.set_facecolor('#f4f2ed'); seeds.draw_moulding(a)
        seeds.envelope.draw(a, reference, 'none', edgecolor='#a5a7a4', linewidth=.8, linestyle='--')
        seeds.envelope.draw(a, e, '#85b3b0', edgecolor='none')
        seeds.envelope.draw(a, hybrid.difference(e), '#d78b48', edgecolor='none')
        seeds.envelope.draw(a, hybrid, 'none', edgecolor='#194a50', linewidth=.8)
        seeds.envelope.draw(a, rods, '#d8b268', edgecolor='#94722e', linewidth=.7)
        a.set(aspect='equal'); a.spines[['top', 'right']].set_visible(False)
        a.set_xlabel('Projection from wall / mm'); a.set_ylabel('Height relative to rear rod / mm')
    ax.set(xlim=(-7, 220), ylim=(-65, 182), title='E frame / F-derived backing in orange')
    zoom.set(xlim=(-3, 212), ylim=(-65, 30), title='One-inch locating lip / deeper frame beyond the moulding')
    zoom.annotate('', xy=(25.4, -51), xytext=(0, -51), arrowprops={'arrowstyle': '<->', 'color': '#6c522e'})
    zoom.text(12.7, -58, '25.4 mm', ha='center', color='#6c522e', fontsize=10)
    fig.suptitle('E + F / deep frame with broader seat-root transitions', fontsize=19, fontweight='bold')
    fig.supxlabel('G locating height and rod/mount positions retained. Brown: crown moulding; pale band: clearance allowance.\nGeometry direction only. Actual body/helper STEP, slicing and mechanics are separate verification stages.', fontsize=10)
    fig.savefig(D / 'direction.png', dpi=170); plt.close(fig)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
