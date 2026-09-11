"""Show actual raw-slice material omitted by the inscribed GPU crop grids."""
from pathlib import Path
import json

import numpy as np
import shapely
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from shapely.geometry.polygon import orient

from plastic_shape import PlasticShape, polygons


def draw(ax, geometry, color):
    for polygon in polygons(geometry):
        polygon = orient(polygon,sign=1.)
        rings = [np.asarray(r.coords) for r in [polygon.exterior,*polygon.interiors]]
        codes = [np.r_[MplPath.MOVETO,np.full(len(r)-2,MplPath.LINETO),MplPath.CLOSEPOLY] for r in rings]
        ax.add_patch(PathPatch(MplPath(np.vstack(rings),np.concatenate(codes)),facecolor=color,edgecolor='none'))


def main():
    root = Path('analysis/rev-g2/gpu-validation')
    shape = PlasticShape.load('analysis/rev-g2/g-recheck/2w-5layers/validated-shape')
    paths = [root/'g-crop-h0p4',root/'g-crop-h0p2',root/'refinement/g-crop-h0p1']
    fig,axes = plt.subplots(2,3,figsize=(11,7.3),sharex=True,sharey=True,layout='constrained')
    for col,path in enumerate(paths):
        report = json.loads(path.with_suffix('.json').read_text())
        cells = np.load(path.with_suffix('.npz'))['cells']
        spacing = np.asarray(report['spacing_mm'])
        lower = np.asarray(report['crop_lower_mm'])
        for row,z in enumerate([.9,12.1]):
            ax = axes[row,col]
            raw = shape.section(z).intersection(shapely.box(140,-34,148,-26))
            ij = cells[cells[:,2] == int(np.floor(z/spacing[2])),:2]
            xy = lower[:2]+ij*spacing[:2]
            solid = shapely.union_all(shapely.box(xy[:,0],xy[:,1],xy[:,0]+spacing[0],xy[:,1]+spacing[1]))
            draw(ax,raw,'#d96853')
            draw(ax,solid,'#226a9a')
            ax.set(xlim=(140,148),ylim=(-34,-26),aspect='equal',xlabel='Installed X (mm)',ylabel='Installed Y (mm)')
            ax.set_title(f'XY {spacing[0]:g} mm; Z = {z:g} mm\n{100*report["omitted_fraction"]:.2f}% volume omitted from full crop',fontsize=10)
    fig.suptitle('Actual G slice crop: retained voxels (blue), omitted material (red)\nGeometry diagnostic; no bracket loading or strength claim',fontsize=13)
    fig.savefig(root/'material-resolution.png',dpi=180)


if __name__ == '__main__':
    main()
