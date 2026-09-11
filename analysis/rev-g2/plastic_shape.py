"""Slicer-backed plastic occupancy, with spent material separate from structure.

Read the emitted G-code, including per-path width and height. Thick bridge
extrusion is spent plastic but is excluded from the structural solid.
"""
from pathlib import Path
import argparse
import hashlib
import gzip
import json
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon
from shapely.geometry.polygon import orient

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(D/'.work/python'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_paths(folder, model_to_installed=None):
    """Absolute XYZ; either absolute or relative E; actual moving extrusion only."""
    if model_to_installed is None:
        model_to_installed = np.array([[-1., 0, 0, 250], [0, -1., 0, 182], [0, 0, 1., 0]])
    with zipfile.ZipFile(folder/'audit.3mf') as archive:
        root = ET.fromstring(archive.read('3D/3dmodel.model'))
        item = root.find('{*}build/{*}item')
        xf = np.array([float(v) for v in item.attrib['transform'].split()]).reshape(4, 3)
    assert np.allclose(xf[:3]@xf[:3].T, np.eye(3), atol=1e-6)
    assert np.allclose(xf[:3, 2], [0, 0, 1], atol=1e-6)
    source = (folder/'plate_1.gcode').read_text(encoding='utf-8')
    diameter = float(re.search(r'; filament_diameter: ([\d.]+)', source).group(1))
    area = np.pi*diameter**2/4
    pos = np.zeros(3)
    relative_E, absolute_XYZ, previous_E = True, True, 0.
    role, width, height, layer_z = 'Custom', .45, .2, None
    points, widths, heights, declared_heights, tops, roles, volumes = [], [], [], [], [], [], []
    nonobject_moving_volume = 0.
    nonobject_moving_segments = 0
    active = False
    for line in source.splitlines():
        if line.startswith('; printing object'):
            active = True
        elif line.startswith('; stop printing object'):
            active = False
        elif line.startswith((';TYPE:', '; FEATURE:')):
            role = line.split(':', 1)[1].strip()
        elif line.startswith((';WIDTH:', '; LINE_WIDTH:')):
            width = float(line.split(':', 1)[1])
        elif line.startswith((';HEIGHT:', '; LAYER_HEIGHT:')):
            height = float(line.split(':', 1)[1])
        elif line.startswith((';Z:', '; Z_HEIGHT:')):
            layer_z = float(line.split(':', 1)[1])
        code = line.split(';')[0].strip()
        command = code.split(' ', 1)[0]
        if command == 'M83':
            relative_E = True
        elif command == 'M82':
            relative_E = False
        elif command == 'G90':
            absolute_XYZ = True
        elif command == 'G91':
            absolute_XYZ = False
        elif command in ['G92', 'G0', 'G1']:
            fields = {k: float(v) for k, v in re.findall(r'([XYZE])([-+\d.eE]+)', code)}
            if command == 'G92':
                if 'E' in fields:
                    previous_E = fields['E']
                for j, k in enumerate('XYZ'):
                    if k in fields:
                        pos[j] = fields[k]
                continue
            new = pos.copy()
            for j, k in enumerate('XYZ'):
                if k in fields:
                    new[j] = fields[k] if absolute_XYZ else new[j]+fields[k]
            extrusion = fields.get('E', 0.) if relative_E else (fields['E']-previous_E if 'E' in fields else 0.)
            if 'E' in fields:
                previous_E = fields['E'] if not relative_E else previous_E+fields['E']
            if active and extrusion > 0 and np.linalg.norm(new[:2]-pos[:2]) > 1e-7:
                assert layer_z is not None and abs(new[2]-layer_z) < 1e-3
                assert abs(new[2]-pos[2]) < 1e-3, 'Nonplanar extruding move needs a 3D sweep'
                model = (np.array([pos, new])-xf[3])@xf[:3].T
                installed = model@model_to_installed[:, :3].T+model_to_installed[:, 3]
                points.append(installed[:, :2])
                widths.append(width)
                # Orca emits 0.199999/0.200001 for nominal 0.2 mm layers.
                # Keep the raw declaration but remove numeric rounding
                # gaps which would falsely disconnect otherwise bonded layers.
                normalized_height = .2 if abs(height-.2) < 1e-5 else height
                heights.append(normalized_height)
                declared_heights.append(height)
                tops.append(round(float(installed[1, 2]), 6))
                roles.append(role)
                volumes.append(extrusion*area)
            elif not active and extrusion > 0 and np.linalg.norm(new[:2]-pos[:2]) > 1e-7:
                # P1S startup priming lines are included in Orca's footer but
                # are outside the printed object. Count spent E separately;
                # never add these paths to structural footprints or bonds.
                nonobject_moving_volume += extrusion*area
                nonobject_moving_segments += 1
            pos = new
    data = {'paths': np.asarray(points), 'width': np.asarray(widths),
            'height': np.asarray(heights), 'declared_height': np.asarray(declared_heights), 'top': np.asarray(tops),
            'role': np.asarray(roles), 'volume': np.asarray(volumes)}
    assert len(points) and np.all(data['height'] > 0) and np.all(data['width'] > 0)
    assert not np.any(data['role'] == 'Sparse infill'), 'Requested 0% base infill was not respected'
    thick = np.char.find(np.char.lower(data['role']), 'bridge') >= 0
    thick &= data['height'] > .2001
    data['structural'] = ~thick
    header_volume = float(re.search(r'; filament used \[cm3\] = ([\d.]+)', source).group(1))*1000
    return data, {'Gcode_sha256': sha(folder/'plate_1.gcode'),
                  'audit_3MF_sha256': sha(folder/'audit.3mf'),
                  'all_moving_extrusion_volume_mm3': float(data['volume'].sum()),
                  'object_moving_extrusion_volume_mm3': float(data['volume'].sum()),
                  'nonobject_moving_extrusion_volume_mm3': nonobject_moving_volume,
                  'nonobject_moving_extrusion_segments': nonobject_moving_segments,
                  'all_print_moving_extrusion_volume_mm3': float(data['volume'].sum()+nonobject_moving_volume),
                  'nonobject_policy': 'Outside-object moving extrusion is spent plastic only, excluded from structural footprints and bonds.',
                  'Orca_footer_volume_mm3': header_volume,
                  'object_only_relative_footer_difference': float(abs(data['volume'].sum()/header_volume-1)),
                  'relative_extrusion_footer_difference': float(abs((data['volume'].sum()+nonobject_moving_volume)/header_volume-1)),
                  'structurally_credited_extrusion_volume_mm3': float(data['volume'][~thick].sum()),
                  'sacrificial_thick_bridge_extrusion_volume_mm3': float(data['volume'][thick].sum()),
                  'thick_bridge_segments': int(thick.sum()),
                  'thick_bridge_heights_mm': sorted(set(data['height'][thick].tolist())),
                  'thick_bridge_policy': 'Spent plastic only; no stiffness, strength or bonded-connection credit.',
                  'maximum_height_comment_rounding_normalization_mm': float(np.max(abs(data['height']-data['declared_height']))),
                  'nominal_layer_height_mm': .2,
                  'model_to_installed_transform': model_to_installed.tolist()}


def polygons(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    return [p for p in geometry.geoms if p.geom_type == 'Polygon']


class PlasticShape:
    """Cached sliced-material geometry for repeated occupancy/thickness queries.

    Coordinates are installed millimetres. Structural material includes only
    credited paths. Queries default to the unmodified nominal footprints;
    the continuum approximation must be requested explicitly.
    """
    def __init__(self, layers, report=None):
        self.layers = layers
        self.report = report or {}
        self.z0 = np.array([v[0] for v in layers])
        self.z1 = np.array([v[1] for v in layers])
        for z0, z1, raw, simple in layers:
            shapely.prepare(raw)
            shapely.prepare(simple)

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        compressed = directory/'layers.json.gz'
        if compressed.exists():
            rows = json.loads(gzip.decompress(compressed.read_bytes()))
        else:
            rows = json.loads((directory/'layers.json').read_text(encoding='utf-8'))
        layers = [(r['z0_mm'], r['z1_mm'], shapely.from_wkb(r['raw_wkb']),
                   shapely.from_wkb(r['simplified_wkb'])) for r in rows]
        return cls(layers, json.loads((directory/'shape-verification.json').read_text(encoding='utf-8')))

    def section(self, z, continuum=False):
        k = int(np.searchsorted(self.z1, z, side='right'))
        if k >= len(self.layers) or z < self.z0[k]:
            return Polygon()
        return self.layers[k][3 if continuum else 2]

    def contains(self, xyz, continuum=False):
        xyz = np.asarray(xyz, dtype=float).reshape(-1, 3)
        result = np.zeros(len(xyz), dtype=bool)
        index = np.searchsorted(self.z1, xyz[:, 2], side='right')
        for k in np.unique(index):
            if k >= len(self.layers):
                continue
            selected = (index == k) & (xyz[:, 2] >= self.z0[k])
            geometry = self.layers[k][3 if continuum else 2]
            result[selected] = shapely.contains_xy(geometry, xyz[selected, 0], xyz[selected, 1])
        return result

    def equivalent_thickness(self, xy, continuum=False):
        """Integrate actual bonded occupancy through print Z for reduced FEM."""
        xy = np.asarray(xy, dtype=float).reshape(-1, 2)
        result = np.zeros(len(xy))
        for z0, z1, raw, simple in self.layers:
            result += shapely.contains_xy(simple if continuum else raw, xy[:, 0], xy[:, 1])*(z1-z0)
        return result

    def volume(self, continuum=False):
        return sum((simple if continuum else raw).area*(z1-z0) for z0, z1, raw, simple in self.layers)

    def integrated_volume(self, regions, continuum=False, workers=4):
        """Return material volume intersecting each supplied XY polygon.

        Each result is independently accumulated through all cached Z slabs;
        overlapping input regions therefore intentionally count in each
        corresponding result.  Full containment uses prepared ``covers`` and
        only partial intersections invoke exact polygon intersection areas.
        Defaults remain raw printed footprints; request ``continuum=True``
        explicitly for simplified footprints.
        """
        regions = np.asarray(tuple(regions), dtype=object)
        if not len(regions):
            return np.zeros(0, dtype=float)
        assert np.all(shapely.is_valid(regions))
        region_areas = shapely.area(regions)
        def one(layer):
            z0, z1, raw, simple = layer
            material = simple if continuum else raw
            covered = np.asarray(shapely.covers(material, regions), dtype=bool)
            partial = np.asarray(shapely.intersects(material, regions), dtype=bool) & ~covered
            areas = np.zeros(len(regions), dtype=float)
            areas[covered] = region_areas[covered]
            areas[partial] = shapely.area(shapely.intersection(material, regions[partial]))
            return areas*(z1-z0)
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            parts = list(pool.map(one, self.layers))
        return np.sum(parts, axis=0)


def layer_shapes(data, workers=4, simplify_mm=.01, close_gap_mm=0., homogenize_holes_mm2=0., coordinate_grid_mm=0.):
    """Union actual credited footprints. No body mask or rectangular core cutter."""
    edges = np.unique(np.round(np.r_[data['top'], data['top']-data['height']], 8))
    credited = data['structural']
    def one(pair):
        z0, z1 = pair
        mid = (z0+z1)/2
        selected = credited & (data['top'] > mid) & (data['top']-data['height'] < mid)
        lines = shapely.linestrings(data['paths'][selected])
        raw = shapely.union_all(shapely.buffer(lines, data['width'][selected]/2, quad_segs=6))
        # Optional printed-material homogenization at the stated gap scale.
        # Preserve the untouched footprint reference and quantify every change.
        # This is geometry preprocessing, independent of stress values.
        continuous = raw.buffer(close_gap_mm, quad_segs=6).buffer(-close_gap_mm, quad_segs=6) if close_gap_mm else raw
        if homogenize_holes_mm2:
            # The continuum uses printed-material properties, which already
            # include sub-bead porosity. Keep the raw gaps for audit; retain
            # every void larger than the explicitly reported area scale.
            continuous = shapely.union_all([Polygon(p.exterior, [ring for ring in p.interiors if Polygon(ring).area >= homogenize_holes_mm2]) for p in polygons(continuous)])
        simple = continuous.simplify(simplify_mm, preserve_topology=True)
        if coordinate_grid_mm:
            simple = shapely.set_precision(simple, coordinate_grid_mm)
        assert raw.is_valid and simple.is_valid
        return (float(z0), float(z1), raw, simple)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        layers = list(pool.map(one, list(zip(edges[:-1], edges[1:]))))
    return layers


def cross_section(geometry):
    import manifold3d as mf
    rings = []
    for p in polygons(geometry):
        p = orient(p, sign=1)
        rings.append(np.asarray(p.exterior.coords)[:-1])
        rings.extend(np.asarray(r.coords)[:-1] for r in p.interiors)
    return mf.CrossSection(rings)


def write_stl(path, p, t):
    triangles = p[t]
    normal = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    length = np.linalg.norm(normal, axis=1)
    normal[length > 0] /= length[length > 0, None]
    a = np.zeros(len(t), dtype=[('normal', '<f4', (3,)), ('points', '<f4', (3, 3)), ('attr', '<u2')])
    a['normal'], a['points'] = normal, triangles
    with path.open('wb') as f:
        f.write(b'Slicer-derived structural material; thick bridges excluded'.ljust(80, b' '))
        f.write(np.uint32(len(t)).tobytes())
        f.write(a.tobytes())


def solid_from_layers(layers, output, tolerance_mm=0.):
    import manifold3d as mf
    solids = [cross_section(simple).extrude(z1-z0).translate((0, 0, z0))
              for z0, z1, raw, simple in layers if not simple.is_empty]
    print('fuse', len(solids), 'actual layer solids', flush=True)
    shape = mf.Manifold.batch_boolean(solids, mf.OpType.Add)
    assert shape.status() == mf.Error.NoError
    before = shape.volume()
    shape = shape.as_original()
    if tolerance_mm > 0:
        shape = shape.simplify(tolerance_mm)
    assert shape.status() == mf.Error.NoError
    mesh = shape.to_mesh64()
    p, t = np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts)
    # Manifold distinguishes property vertices from topological vertices.
    # Apply only its explicit weld map; coordinate rounding can wrongly join
    # separate point contacts or collapse real finite triangles.
    weld = np.arange(len(p))
    weld[np.asarray(mesh.merge_from_vert, dtype=int)] = np.asarray(mesh.merge_to_vert, dtype=int)
    while not np.array_equal(weld, weld[weld]):
        weld = weld[weld]
    used, inverse = np.unique(weld[t], return_inverse=True)
    p, t = p[used], inverse.reshape(-1, 3)
    edges = np.sort(t[:, [(0, 1), (1, 2), (2, 0)]].reshape(-1, 2), axis=1)
    _, incidence = np.unique(edges, axis=0, return_counts=True)
    assert np.all(incidence == 2), 'Structural surface is not closed/manifold'
    np.savez_compressed(output/'surface.npz', p=p, t=t)
    write_stl(output/'structural-material.stl', p, t)
    return {'solid_volume_before_surface_simplification_mm3': before,
            'solid_volume_mm3': shape.volume(),
            **bond_connectivity(layers),
            'vertices': len(p), 'triangles': len(t),
            'surface_edge_incidence_all_two': True,
            'maximum_surface_simplification_tolerance_mm': tolerance_mm,
            'surface_STL_sha256': sha(output/'structural-material.stl')}


def bond_connectivity(layers):
    # Count bonded material through planar regions, not boundary components:
    # an enclosed air cavity adds a surface component but not another solid.
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    regions = [polygons(simple) for z0, z1, raw, simple in layers]
    offsets = np.r_[0, np.cumsum([len(parts) for parts in regions])]
    links = []
    for k in range(1, len(regions)):
        if not regions[k-1] or not regions[k]:
            continue
        tree = shapely.STRtree(regions[k-1])
        for i, poly in enumerate(regions[k]):
            for j in tree.query(poly, predicate='intersects'):
                if poly.intersection(regions[k-1][j]).area > 1e-8:
                    links.append((offsets[k]+i, offsets[k-1]+j))
    links = np.asarray(links, dtype=int).reshape(-1, 2)
    graph = coo_matrix((np.ones(len(links)), (links[:, 0], links[:, 1])), shape=(offsets[-1], offsets[-1]))
    count, labels = connected_components(graph, directed=False)
    component_volumes = np.zeros(count)
    for k, (z0, z1, raw, simple) in enumerate(layers):
        for i, poly in enumerate(regions[k]):
            component_volumes[labels[offsets[k]+i]] += poly.area*(z1-z0)
    return {'connected_structural_components': int(count),
            'component_volumes_mm3': sorted(component_volumes.tolist(), reverse=True),
            'connection_definition': 'Positive-area overlap of credited material on consecutive layer interfaces; no thick-bridge connection.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('slice_directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--simplify-mm', type=float, default=.01)
    parser.add_argument('--close-gap-mm', type=float, default=0.)
    parser.add_argument('--homogenize-holes-mm2', type=float, default=0.)
    parser.add_argument('--coordinate-grid-mm', type=float, default=0.)
    parser.add_argument('--surface-simplify-mm', type=float, default=0.)
    parser.add_argument('--solid', action='store_true')
    args = parser.parse_args()
    start = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)
    data, report = read_paths(args.slice_directory)
    assert report['relative_extrusion_footer_difference'] < .001
    np.savez_compressed(args.output/'extrusion-paths.npz', **data)
    print('parsed', len(data['paths']), 'paths', flush=True)
    layers = layer_shapes(data, args.workers, args.simplify_mm, args.close_gap_mm, args.homogenize_holes_mm2, args.coordinate_grid_mm)
    rows = [{'z0_mm': z0, 'z1_mm': z1, 'raw_area_mm2': raw.area,
             'simplified_area_mm2': simple.area,
             'symmetric_difference_area_mm2': raw.symmetric_difference(simple).area,
             'connected_planar_regions': len(polygons(simple)),
             'raw_wkb': raw.wkb_hex, 'simplified_wkb': simple.wkb_hex}
            for z0, z1, raw, simple in layers]
    (args.output/'layers.json.gz').write_bytes(gzip.compress(json.dumps(rows, separators=(',', ':')).encode(), mtime=0))
    report['layer_cache_sha256'] = sha(args.output/'layers.json.gz')
    report['nominal_footprint_union_volume_mm3'] = sum(raw.area*(z1-z0) for z0, z1, raw, simple in layers)
    report['layer_polygon_volume_mm3'] = sum(simple.area*(z1-z0) for z0, z1, raw, simple in layers)
    report['shape_relative_difference_from_credited_extrusion_volume'] = report['layer_polygon_volume_mm3']/report['structurally_credited_extrusion_volume_mm3']-1
    report['layers'] = len(layers)
    report['polygon_simplification_tolerance_mm'] = args.simplify_mm
    report['homogenization_gap_closing_radius_mm'] = args.close_gap_mm
    report['printed_material_homogenized_void_area_limit_mm2'] = args.homogenize_holes_mm2
    report['coordinate_grid_mm'] = args.coordinate_grid_mm
    report['integrated_shape_reference_symmetric_difference_mm3'] = sum(raw.symmetric_difference(simple).area*(z1-z0) for z0, z1, raw, simple in layers)
    report['source_sha256_LF_UTF8'] = hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest()
    report['shape_model'] = 'Union of emitted nominal bead-width footprints extruded through their declared heights. Thick bridges are excluded. No inherited CAD core or shell approximation.'
    report['volume_interpretation'] = 'G-code E gives spent and credited extrusion volumes. Footprint union gives the homogenized structural envelope; its measured difference from E is reported, never silently equated.'
    report['bond_connectivity'] = bond_connectivity(layers)
    (args.output/'shape-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if args.solid:
        report['solid'] = solid_from_layers(layers, args.output, args.surface_simplify_mm)
    report['elapsed_seconds'] = time.perf_counter()-start
    report['status'] = 'GEOMETRY BUILT; mechanics and approximation validation are separate.'
    (args.output/'shape-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
