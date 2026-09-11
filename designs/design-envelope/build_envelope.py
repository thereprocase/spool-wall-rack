"""Build and audit the allowable post-G XY design domain; not a new bracket."""
from pathlib import Path
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box, mapping
from shapely import union_all
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
BG, INK, TEAL, GOLD = '#f3f1e9', '#243d43', '#a6cbc4', '#c28a30'


def text_sha256(path):
    # Normalize checkout line endings so published source has the same digest.
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def read_reference(definition):
    path = ROOT/definition['space_limits']['underside_reference_profile']
    svg = ET.parse(path).getroot()
    text = svg.find('{http://www.w3.org/2000/svg}path').attrib['d']
    poly = Polygon([(float(x), -float(y)) for x, y in re.findall(r'([-+\d.eE]+),([-+\d.eE]+)', text)])
    assert poly.is_valid
    return poly, path


def lower_trace(poly):
    # The lowest crossing can change only at a vertex X for a simple polygon.
    # Collinear intermediate coordinates are removed without changing the limit.
    xs = sorted(set(x for x, y in poly.exterior.coords))
    values = []
    for x in xs:
        section = poly.intersection(LineString([(x, -1000), (x, 1000)]))
        assert not section.is_empty
        values.append((x, section.bounds[1]))
    return np.asarray(LineString(values).simplify(1e-10).coords)


def circle(center, radius, segments):
    # Circumscribed polygon, so the analytical circle is never undercut.
    return Point(*center).buffer(radius/math.cos(math.pi/(4*segments)), quad_segs=segments)


def build(definition):
    baseline, source = read_reference(definition)
    limits = definition['space_limits']; floor = lower_trace(baseline)
    floor[:, 1] -= limits['maximum_extra_downward_drop_mm']
    if floor[-1, 0] < limits['maximum_projection_X_mm']:
        floor = np.vstack([floor, [limits['maximum_projection_X_mm'], floor[-1, 1]]])
    frame = Polygon([*map(tuple, floor),
                     (limits['maximum_projection_X_mm'], limits['maximum_height_Y_mm']),
                     (limits['wall_plane_X_mm'], limits['maximum_height_Y_mm'])])
    assert frame.is_valid
    space = definition['spool_clearance']; centers = definition['functional_requirements']['rail_centers_XY_mm']
    a, b = map(np.asarray, centers); delta = b-a; spacing = float(np.linalg.norm(delta))
    normal = np.array([-delta[1], delta[0]])/spacing; midpoint = (a+b)/2
    rmin, rmax = space['effective_rail_radius_interval_mm']
    dmin, dmax = space['diameter_interval_mm']; step = space['diameter_sampling_step_mm']
    # Rail-radius variation moves the center along one straight segment, so a
    # capsule covers its full continuous range exactly for each spool radius.
    # For an intermediate diameter, nearest sample differs in radius by step/4.
    # Hausdorff motion <= delta_R * (1 + max q'(R+r)), where q'=T/sqrt(T²-S²/4).
    tmin = dmin/2+rmin; max_derivative = tmin/math.sqrt(tmin*tmin-spacing*spacing/4)
    necessary_guard = step/4*(1+max_derivative)
    assert space['continuous_sweep_guard_mm'] >= necessary_guard
    capsules = []
    for diameter in np.linspace(dmin, dmax, round((dmax-dmin)/step)+1):
        radius = diameter/2
        ends = [midpoint+normal*math.sqrt((radius+rr)**2-spacing**2/4) for rr in [rmin, rmax]]
        extra = space['minimum_nominal_clearance_mm']+space['continuous_sweep_guard_mm']
        compensated_radius = (radius+extra)/math.cos(math.pi/(4*space['circle_quadrant_segments']))
        capsules.append(LineString(ends).buffer(compensated_radius, quad_segs=space['circle_quadrant_segments']))
    spool_keepout = union_all(capsules)
    rod_radius = definition['functional_requirements']['nominal_rod_diameter_mm']/2
    rod_keepout = union_all([circle(center, rod_radius, space['circle_quadrant_segments']) for center in centers])
    allowed = frame.difference(spool_keepout.union(rod_keepout))
    assert allowed.is_valid and not allowed.is_empty
    return baseline, source, floor, frame, spool_keepout, rod_keepout, allowed, necessary_guard


def check_xy(candidate, allowed, tolerance_mm2=1e-6):
    outside = candidate.difference(allowed).area
    return {'outside_allowed_XY_area_mm2': float(outside),
            'passes_spatial_XY_gate': bool(candidate.is_valid and outside <= tolerance_mm2),
            'scope': 'Spatial occupancy only. Fit, retention, fixings, connected load paths, density coverage and mechanics remain separate gates.'}


def draw(ax, geometry, color, **kwargs):
    polygons = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    for p in polygons:
        if p.is_empty: continue
        from shapely.geometry.polygon import orient
        p = orient(p, sign=1); vertices, codes = [], []
        for ring in [p.exterior, *p.interiors]:
            points = list(ring.coords); vertices.extend(points)
            codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(points)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(vertices, codes), facecolor=color, **kwargs))


def render(definition, baseline, floor, frame, spool, rods, allowed):
    fig, (ax, zoom) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={'width_ratios': [1, 1.25]},
                                  layout='constrained', facecolor=BG)
    for panel in [ax, zoom]:
        panel.set_facecolor(BG)
        draw(panel, frame.intersection(spool), '#d9dcdb', edgecolor='none')
        draw(panel, allowed, TEAL, edgecolor='#4b8a83', linewidth=.7)
        draw(panel, baseline, '#f3f1e9', edgecolor=INK, linewidth=.9)
        draw(panel, rods, '#d5b576', edgecolor='#987b46', linewidth=.8)
        panel.plot(floor[:, 0], floor[:, 1], color=GOLD, lw=2)
        panel.spines[['top', 'right']].set_visible(False)
        panel.set(aspect='equal', xlabel='Projection from wall X (mm)', ylabel='Installed height Y (mm)')
    ax.set(xlim=(-8, 225), ylim=(-60, 190), title='Allowable space / existing body shown for scale')
    ax.annotate('Spool clearance exclusion\n180–220 mm flanges', xy=(75, 130), xytext=(80, 164),
                fontsize=9, arrowprops={'arrowstyle': '-', 'color': INK})
    ax.annotate('Wall plane / X = 0', xy=(0, 110), xytext=(42, 110), fontsize=9,
                arrowprops={'arrowstyle': '-', 'color': INK})
    ax.text(110, -57, 'Printed width: 24 mm (Z = 0–24)', ha='center', fontsize=9)
    zoom.set(xlim=(-2, 220), ylim=(-61, 32), title='Underside limit / up to 8 mm extra local drop')
    zoom.plot([76, 104], [-43, -43], color=INK, lw=1.5)
    zoom.annotate('', xy=(90, -51), xytext=(90, -43), arrowprops={'arrowstyle': '<->', 'color': '#875b13'})
    zoom.text(94, -47, '8 mm', va='center', fontsize=10, color='#875b13')
    zoom.annotate('Current lowest point: Y = −43 mm', xy=(83, -43), xytext=(10, -56), fontsize=9,
                  arrowprops={'arrowstyle': '-', 'color': INK})
    zoom.annotate('Absolute lower limit: Y = −51 mm', xy=(100, -51), xytext=(119, -56), fontsize=9,
                  arrowprops={'arrowstyle': '-', 'color': '#875b13'})
    fig.suptitle('POST-G / a design envelope, with freedom to remove and redistribute material',
                 fontsize=17, fontweight='bold', color=INK)
    fig.supxlabel('Green: available design space · ivory: existing body, not mandatory material · gray: spool exclusion · gold line: lower limit.\nOuter shape, walls, skins, ribs and voids may change. Any number of 100% infill helpers may redistribute density; functional and mechanical gates still apply.', fontsize=10)
    fig.savefig(D/'design-envelope.png', dpi=180); plt.close(fig)


def main():
    definition = json.loads((D/'definition.json').read_text(encoding='utf-8'))
    baseline, source, floor, frame, spool, rods, allowed, guard = build(definition)
    probes = {'existing_E13_profile': baseline,
              'remove_material_inside_arm': baseline.difference(box(120, -28, 144, -18)),
              'add_material_6mm_below_wall_end': baseline.union(box(8, -38, 18, -30)),
              'reject_9mm_drop_at_wall_end': baseline.union(box(8, -41, 18, -30)),
              'reject_wall_penetration': baseline.union(box(-1, -25, 2, -20))}
    checks = {name: check_xy(poly, allowed) for name, poly in probes.items()}
    for name, result in checks.items():
        assert result['passes_spatial_XY_gate'] == (not name.startswith('reject_')), (name, result)
    features = []
    for name, shape in [('allowed_XY_domain', allowed), ('spool_exclusion', spool),
                        ('nominal_rod_exclusion', rods), ('reference_body_not_required', baseline)]:
        features.append({'type': 'Feature', 'properties': {'name': name}, 'geometry': mapping(shape)})
    (D/'design-domain.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':'))+'\n', encoding='utf-8')
    record = {'status': 'PASS: envelope construction and spatial probes only',
              'hash_representation': 'UTF-8 text with LF line endings',
              'definition_sha256': text_sha256(D/'definition.json'),
              'reference_profile_sha256': text_sha256(source),
              'builder_sha256': text_sha256(Path(__file__)),
              'reference_profile_bounds_XY_mm': list(baseline.bounds), 'allowed_domain_bounds_XY_mm': list(allowed.bounds),
              'maximum_extra_local_drop_mm': definition['space_limits']['maximum_extra_downward_drop_mm'],
              'absolute_lowest_Y_mm': float(floor[:, 1].min()),
              'required_continuous_diameter_guard_mm': guard,
              'applied_continuous_diameter_guard_mm': definition['spool_clearance']['continuous_sweep_guard_mm'],
              'spatial_probes': checks, 'frozen_material_regions': 0, 'helper_count_limit': None,
              'new_bracket_optimized': False, 'expanded_shape_search_implemented': False,
              'limitations': 'The XY domain is extruded through Z=0..24 for spatial occupancy. Screw/driver clearance and washer support are 3D functional requirements, not removed from this side-view drawing. No strength, retention or physical qualification is inferred.'}
    (D/'verification.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    render(definition, baseline, floor, frame, spool, rods, allowed)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
