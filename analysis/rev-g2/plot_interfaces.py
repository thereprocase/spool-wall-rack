"""Plot nodes selected by the production interface classifier, without solving."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
import numpy as np
import shapely
from shapely.geometry import LineString, box
from shapely.geometry.polygon import orient

from solve_plastic import solve
from plastic_shape import PlasticShape, polygons


def fill_region(ax, region):
    for poly in polygons(region):
        poly = orient(poly, sign=1.)
        paths = []
        for ring in [poly.exterior, *poly.interiors]:
            vertices = np.array(ring.coords)
            codes = np.full(len(vertices), PlotPath.LINETO)
            codes[0], codes[-1] = PlotPath.MOVETO, PlotPath.CLOSEPOLY
            paths.append(PlotPath(vertices, codes))
        ax.add_patch(PathPatch(PlotPath.make_compound_path(*paths), facecolor='#e1e5e9',
                               edgecolor='#a3adb9', lw=.5))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mesh-description', default='Interface classification diagnostic')
    parser.add_argument('--shape-directory', type=Path)
    args = parser.parse_args()
    data = solve(SimpleNamespace(mesh=args.mesh, output=args.output, E=1000., nu=.35,
                                 surface_tolerance_mm=.05, load_N=117.72,
                                 interfaces_only=True, flat_wall_reference=False))
    p = data['points']
    shape = PlasticShape.load(args.shape_directory or args.mesh.parent)
    side_projection = shapely.union_all([row[3] for row in shape.layers])
    wall_sections = []
    for z0, z1, _raw, poly in shape.layers:
        for line in shapely.get_parts(poly.intersection(LineString([(3.6, -60), (3.6, 190)]))):
            if line.geom_type == 'LineString' and line.length > 0:
                wall_sections.append(box(z0, line.bounds[1], z1, line.bounds[3]))
    washer_plane_section = shapely.union_all(wall_sections)
    fig, axes = plt.subplots(1, 2, figsize=(12, 7), gridspec_kw={'width_ratios': [1.8, 1]})
    groups = [('Wall candidates', data['wall'], '#be4b36'),
              ('Washer axial restraint', np.concatenate(list(data['heads'].values())), '#b27610'),
              ('Screw shank bearing', np.concatenate(list(data['bores'].values())), '#7548a4'),
              ('Rod bearing loads', np.concatenate([v['nodes'] for v in data['patches'].values()]), '#006c9f')]
    for ax, indices, xlabel, title in [(axes[0], (0, 1), 'X outward from wall, mm', 'Installed side view'),
                                      (axes[1], (2, 1), 'Z across bracket, mm', 'Wall-side interface view')]:
        if indices == (0, 1):
            fill_region(ax, side_projection)
        else:
            fill_region(ax, washer_plane_section)
        for label, nodes, color in groups:
            if indices == (2, 1) and label == 'Rod bearing loads':
                continue
            q = p[nodes]
            ax.scatter(q[:, indices[0]], q[:, indices[1]], s=2.5, c=color, label=label, rasterized=True)
        ax.set(xlabel=xlabel, ylabel='Y vertical, mm', title=title)
        ax.set_aspect('equal')
        ax.grid(alpha=.15)
    for (label, xy) in [('rear_seat', (90, 0)), ('front_seat', (190, 12))]:
        force = np.array(data['patches'][label]['force_N'])
        delta = force[:2]*.35
        axes[0].annotate('', xy=np.array(xy)+delta, xytext=xy,
                         arrowprops={'arrowstyle': '->', 'color': '#006c9f', 'lw': 2})
        axes[0].text(xy[0]+7, xy[1]+20, f'{label.replace("_seat", "")}\n({force[0]:.1f}, {force[1]:.1f}) N', fontsize=9)
    axes[0].legend(loc='upper right', fontsize=8, markerscale=3)
    axes[0].set_xlim(-10, 222)
    axes[0].set_ylim(-58, 188)
    axes[1].set_xlim(-2, 26)
    fig.suptitle(args.mesh_description, fontsize=13)
    fig.text(.5, .035, 'Grey: layer-union XY projection / X=3.6 mm section. Colored nodes: production interface classifier.', ha='center', fontsize=9)
    fig.tight_layout(rect=[0, .05, 1, .95])
    fig.savefig(args.output.with_suffix('.png'), dpi=170)
    print(json.dumps({'image': args.output.with_suffix('.png').name,
                      'bearing_interfaces': data['report']['bearing_interfaces']}), flush=True)


if __name__ == '__main__':
    main()
