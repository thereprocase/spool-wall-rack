"""Compare archived G finite material with its actual Orca extrusion footprints.

This diagnoses the material mapping; it does not turn G's old stress field into
a strength result for a corrected domain. No old fields or CAD are modified.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, box, Point
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT/'designs/closed-wall-e13'))
spec = importlib.util.spec_from_file_location('g_path_reader', ROOT/'designs/closed-wall-e13/inspect_toolpaths.py')
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)
EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def section(vertices, axis, coordinate, bounds, stresses=None):
    """Exact planar cuts of every intersected finite tetrahedron in the ROI."""
    other = [k for k in range(3) if k != axis]
    mask = ((vertices[:, :, axis].min(1) < coordinate)
            & (vertices[:, :, axis].max(1) > coordinate))
    for j, k in enumerate(other):
        mask &= ((vertices[:, :, k].max(1) >= bounds[j])
                 & (vertices[:, :, k].min(1) <= bounds[j+2]))
    polygons, values = [], []
    for index in np.flatnonzero(mask):
        tetra = vertices[index]
        points = []
        for a, b in EDGES:
            za, zb = tetra[a, axis]-coordinate, tetra[b, axis]-coordinate
            if za*zb < 0:
                point = tetra[a]+(-za/(zb-za))*(tetra[b]-tetra[a])
                points.append(point[other])
            elif za == 0:
                points.append(tetra[a, other])
            elif zb == 0:
                points.append(tetra[b, other])
        points = np.unique(np.asarray(points), axis=0)
        if len(points) < 3:
            continue
        center = points.mean(0)
        order = np.argsort(np.arctan2(points[:, 1]-center[1], points[:, 0]-center[0]))
        poly = Polygon(points[order])
        if poly.area > 0:
            polygons.append(poly)
            if stresses is not None:
                values.append(float(stresses[index]))
    merged = shapely.union_all(polygons).intersection(box(*bounds))
    return merged, polygons, values


def draw_boundary(ax, geometry, color, **kwargs):
    for p in (list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]):
        if p.is_empty or not hasattr(p, 'exterior'):
            continue
        for ring in [p.exterior, *p.interiors]:
            a = np.asarray(ring.coords)
            ax.plot(a[:, 0], a[:, 1], color=color, **kwargs)


def line_intervals(geometry, x, ymin, ymax):
    intersection = geometry.intersection(LineString([(x, ymin), (x, ymax)]))
    result = []
    for part in (list(intersection.geoms) if hasattr(intersection, 'geoms') else [intersection]):
        if not part.is_empty and part.length > 1e-9:
            result.append((part.bounds[1], part.bounds[3]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--slice-directory', type=Path, required=True)
    args = parser.parse_args()
    output = D/'g-slicer-mapping'
    output.mkdir(exist_ok=True)
    field = ROOT/'analysis/rev-g/studies/full-plane-best/print-material-1w-h1-solution.npz'
    expected = json.loads((ROOT/'designs/rev-g/toolpath-verification.json').read_text())
    gcode = args.slice_directory/'plate_1.gcode'
    digest = hashlib.sha256(gcode.read_bytes()).hexdigest()
    assert digest == expected['gcode_sha256'], 'Wrong archived G slice'
    pth, width, role, layer, transform = paths.parse(args.slice_directory)
    with np.load(field) as data:
        p, t, stress = data['p'], data['t'], data['stress']
    principal = np.linalg.eigvalsh(stress.transpose(2, 0, 1))[:, -1]
    peak = int(np.argmax(principal))
    peak_center = p[t[peak]].mean(0)
    vertices = p[t]
    roi_bounds = [130., -37., 160., -19.]
    roi = box(*roi_bounds)
    local = ((pth[:, :, 0].max(1) > roi_bounds[0]-1)
             & (pth[:, :, 0].min(1) < roi_bounds[2]+1)
             & (pth[:, :, 1].max(1) > roi_bounds[1]-1)
             & (pth[:, :, 1].min(1) < roi_bounds[3]+1))
    rows, prints, models = [], {}, {}
    for k in range(120):
        if k % 10 == 0:
            print('slice mapping', k+1, flush=True)
        z = (k+.5)*.2
        material, _, _ = section(vertices, 2, z, roi_bounds)
        selected = (layer == k) & local & (role != 'Sparse infill')
        emitted = paths.union_footprints(pth, width, selected).intersection(roi)
        prints[k] = emitted
        models[k] = material
        extra = emitted.difference(material.buffer(.03))
        missing = material.difference(emitted.buffer(.03))
        rows.append({'layer_number': k+1, 'z_mid_mm': z,
                     'FEM_structural_area_mm2': material.area,
                     'emitted_nonsparse_footprint_area_mm2': emitted.area,
                     'emitted_area_outside_FEM_beyond_0p03mm_mm2': extra.area,
                     'FEM_area_uncovered_beyond_0p03mm_mm2': missing.area,
                     'emitted_roles': sorted(set(role[selected]))})
    settings = json.loads((args.slice_directory/'effective-settings.json').read_text())
    keys = ['ensure_vertical_shell_thickness', 'wall_loops', 'top_shell_layers',
            'top_shell_thickness', 'bottom_shell_layers', 'bottom_shell_thickness',
            'infill_wall_overlap', 'top_bottom_infill_wall_overlap', 'thick_internal_bridges']
    record = {'status': 'DIAGNOSTIC: archived FEM versus emitted material',
              'G_Gcode_sha256': digest, 'G_field_sha256': hashlib.sha256(field.read_bytes()).hexdigest(),
              'source_reader': 'designs/closed-wall-e13/inspect_toolpaths.py',
              'slice_transform': transform.tolist(),
              'effective_settings': {k: settings.get(k) for k in keys},
              'ROI_XY_mm': roi_bounds, 'raw_G_peak_cell': peak,
              'raw_G_peak_tensile_MPa': float(principal[peak]),
              'raw_G_peak_cell_center_XYZ_mm': peak_center.tolist(),
              'sum_emitted_nonsparse_footprint_area_times_layer_height_mm3': sum(r['emitted_nonsparse_footprint_area_mm2']*.2 for r in rows),
              'sum_FEM_cross_section_area_times_layer_height_mm3': sum(r['FEM_structural_area_mm2']*.2 for r in rows),
              'sum_emitted_extra_area_times_layer_height_mm3': sum(r['emitted_area_outside_FEM_beyond_0p03mm_mm2']*.2 for r in rows),
              'sum_FEM_uncovered_area_times_layer_height_mm3': sum(r['FEM_area_uncovered_beyond_0p03mm_mm2']*.2 for r in rows),
              'layers': rows,
              'limitations': 'Nominal widths define footprint occupancy, not microscopic bead shape or bond quality. Sparse infill is excluded. Integrals use layer midplanes. This diagnoses mapping and cannot reuse old stress as corrected-domain strength.'}
    (output/'comparison.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    features = []
    for k in range(120):
        for label, geometry in [('emitted_nonsparse', prints[k]), ('archived_FEM', models[k])]:
            features.append({'type': 'Feature', 'properties': {'layer_number': k+1, 'source': label}, 'geometry': shapely.geometry.mapping(geometry)})
    (output/'local-layer-geometry.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':'))+'\n', encoding='utf-8')
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), layout='constrained', facecolor='#f3f1e9')
    for ax, k in zip(axes[0], [109, 114, 115]):
        select = (layer == k) & local & (role != 'Sparse infill')
        ax.add_collection(LineCollection(pth[select], colors='#b27c24', linewidths=.75))
        draw_boundary(ax, models[k], '#126e7d', linewidth=1)
        ax.scatter(*peak_center[:2], marker='x', color='#a83228')
        ax.set(xlim=(138, 152), ylim=(-34, -24), aspect='equal',
               title=f'Layer {k+1}: Z={(k+.5)*.2:.1f} mm', xlabel='X (mm)', ylabel='Y (mm)')
    x = float(peak_center[0])
    section_bounds = [-34., 19., -22., 24.]
    model_yz, polygons, values = section(vertices, 0, x, section_bounds, principal)
    tiles = []
    for k in range(95, 120):
        for ymin, ymax in line_intervals(prints[k], x, -34, -22):
            tiles.append(box(ymin, k*.2, ymax, (k+1)*.2))
    printed_yz = shapely.union_all(tiles)
    axes[1, 0].add_collection(PolyCollection([np.asarray(poly.exterior.coords) for poly in polygons], array=np.asarray(values), cmap='magma', clim=(0, float(principal[peak]))))
    axes[1, 0].set_title('Archived FEM finite cells / tensile stress')
    axes[1, 1].add_collection(PolyCollection([np.asarray(poly.exterior.coords) for poly in tiles], facecolor='#d5a44e', edgecolor='none'))
    axes[1, 1].set_title('Actual nonsparse layer footprints')
    draw_boundary(axes[1, 2], model_yz, '#126e7d', linewidth=1.1)
    draw_boundary(axes[1, 2], printed_yz, '#b27c24', linewidth=1)
    axes[1, 2].set_title('Overlay / teal FEM, gold emitted material')
    for ax in axes[1]:
        ax.scatter(peak_center[1], peak_center[2], marker='x', color='#a83228')
        ax.set(xlim=(-34, -22), ylim=(19, 24.15), aspect='equal', xlabel=f'Y (mm), cut at X={x:.3f}', ylabel='Build Z (mm)')
    fig.suptitle('G2 regression audit / did the G FEM model the material Orca actually prints?', fontsize=17)
    fig.supxlabel('Same archived G-code and h1 field. Red cross: old raw peak. Gold excludes sparse infill.\nFootprints show nominal bead widths; old stress is not a prediction for the corrected geometry.', fontsize=10)
    fig.savefig(output/'mapping-sections.png', dpi=180)
    plt.close(fig)
    print(json.dumps({k: v for k, v in record.items() if k != 'layers'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
